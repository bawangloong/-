"""检查标注、划分，以及图像的完全重复和近似重复。

近似重复使用 8×8 平均哈希。PNG、BMP、PPM、PGM 只用标准库。
JPEG 等其他格式在安装了 Pillow 时才能算近似哈希；算不出时检查失败，避免漏报。
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("development", "library", "validation", "final_test")
NEAR_HAMMING_THRESHOLD = 5
IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".ppm",
    ".pgm",
    ".webp",
    ".tif",
    ".tiff",
}
PRESENCE_TAGS = ("no_plate", "single_plate", "multi_plate")
COLOR_TAGS = {
    "blue": "color_blue",
    "yellow": "color_yellow",
    "green": "color_green",
    "white": "color_white",
    "black": "color_black",
}
CONDITION_TAGS = ("tilt", "blur", "glare")
ORIGINS = ("self_captured", "public", "synthetic", "unknown")


def _metrics():
    path = ROOT / "eval" / "metrics.py"
    spec = importlib.util.spec_from_file_location("plate_metrics", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


METRICS = _metrics()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    records = []
    if not path.is_file():
        return records
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            records.append(json.loads(text))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no} 不是合法 JSON：{exc}") from exc
    return records


def validate_manifest(manifest: dict) -> list[str]:
    errors = []
    if not isinstance(manifest, dict):
        return ["清单必须是 JSON 对象"]
    names = manifest.get("frozen_split_names")
    if list(names or []) != list(SPLITS):
        errors.append("frozen_split_names 必须正好是 development、library、validation、final_test")
    splits = manifest.get("splits")
    if not isinstance(splits, dict):
        return errors + ["缺少 splits 对象"]
    if set(splits) != set(SPLITS):
        errors.append("splits 必须正好包含四个固定划分")
    seen = {}
    for name in SPLITS:
        ids = splits.get(name)
        if not isinstance(ids, list):
            errors.append(f"{name} 必须是 image_id 数组")
            continue
        for image_id in ids:
            if not isinstance(image_id, str) or image_id.strip() == "" or any(ch.isspace() for ch in image_id):
                errors.append(f"{name} 里有非法 image_id：{image_id!r}")
                continue
            if image_id.startswith("EXAMPLE_"):
                errors.append(f"{image_id} 是示例编号，不能进入清单")
            if image_id in seen:
                errors.append(f"{image_id} 同时出现在 {seen[image_id]} 和 {name}")
            else:
                seen[image_id] = name
    evaluate_splits = manifest.get("evaluate_splits")
    if list(evaluate_splits or []) != ["validation", "final_test"]:
        errors.append("evaluate_splits 必须是 validation、final_test")
    blocked = manifest.get("library_must_not_overlap")
    if list(blocked or []) != ["validation", "final_test"]:
        errors.append("library_must_not_overlap 必须是 validation、final_test")
    return errors


ANNOTATION_KEYS = {
    "image_id",
    "relative_path",
    "width",
    "height",
    "source",
    "purpose",
    "category",
    "has_plate",
    "plates",
    "conditions",
    "_example",
    "_comment",
    "notes",
    "annotator",
    "reviewed",
}
PLATE_KEYS = {
    "plate_id",
    "box",
    "number",
    "color",
    "char_count",
    "chars",
    "readable",
    "quad",
    "notes",
}
SOURCE_KEYS = {"origin", "name", "license", "url", "note"}


def validate_annotation(record: dict, allow_example: bool = False) -> list[str]:
    errors = []
    if not isinstance(record, dict):
        return ["标注必须是 JSON 对象"]
    extra = set(record) - ANNOTATION_KEYS
    if extra:
        errors.append("标注有未定义字段：" + "、".join(sorted(extra)))
    if record.get("_example") and not allow_example:
        errors.append("示例标注不能进入正式标注文件")
    image_id = record.get("image_id")
    if not isinstance(image_id, str) or image_id.strip() == "":
        errors.append("缺少 image_id")
    elif (not allow_example) and image_id.startswith("EXAMPLE_"):
        errors.append("正式标注不能使用 EXAMPLE_ 编号")
    relative = record.get("relative_path")
    if not isinstance(relative, str) or relative.strip() == "":
        errors.append("缺少 relative_path")
    purpose = record.get("purpose")
    if purpose not in SPLITS:
        errors.append("purpose 必须是 development、library、validation、final_test 之一")
    if isinstance(relative, str) and purpose in SPLITS:
        prefix = f"data/raw/{purpose}/"
        if not relative.replace("\\", "/").startswith(prefix):
            errors.append(f"relative_path 必须以 {prefix} 开头")
    for key in ("width", "height"):
        value = record.get(key)
        if not isinstance(value, int) or value < 0:
            errors.append(f"{key} 必须是非负整数")
    source = record.get("source")
    if not isinstance(source, dict):
        errors.append("缺少 source")
    else:
        extra_source = set(source) - SOURCE_KEYS
        if extra_source:
            errors.append("source 有未定义字段：" + "、".join(sorted(extra_source)))
        if source.get("origin") not in ORIGINS:
            errors.append("source.origin 必须是 self_captured、public、synthetic、unknown 之一")
        if not isinstance(source.get("name"), str) or source.get("name", "").strip() == "":
            errors.append("source.name 不能为空")
        if not isinstance(source.get("license"), str) or source.get("license", "").strip() == "":
            errors.append("source.license 不能为空")
        if "url" in source and not isinstance(source["url"], str):
            errors.append("source.url 必须是字符串")
    conditions = record.get("conditions")
    if not isinstance(conditions, dict):
        errors.append("缺少 conditions")
        conditions = {}
    else:
        extra_conditions = set(conditions) - set(CONDITION_TAGS)
        if extra_conditions:
            errors.append("conditions 有未定义字段：" + "、".join(sorted(extra_conditions)))
        for key in CONDITION_TAGS:
            if not isinstance(conditions.get(key), bool):
                errors.append(f"conditions.{key} 必须是布尔值")
    category = record.get("category")
    if not isinstance(category, list) or not all(isinstance(item, str) for item in category or []):
        errors.append("category 必须是字符串数组")
        category = []
    else:
        unknown_tags = [
            item
            for item in category
            if item not in PRESENCE_TAGS
            and item not in COLOR_TAGS.values()
            and item not in CONDITION_TAGS
            and item not in ("normal", "other")
        ]
        for item in unknown_tags:
            errors.append(f"未知 category：{item}")
    plates = record.get("plates")
    if not isinstance(plates, list):
        errors.append("plates 必须是数组")
        plates = []
    has_plate = record.get("has_plate")
    if not isinstance(has_plate, bool):
        errors.append("has_plate 必须是布尔值")
    elif has_plate != (len(plates) > 0):
        errors.append("has_plate 必须与 plates 是否非空一致")
    presence = [tag for tag in PRESENCE_TAGS if tag in category]
    if len(presence) != 1:
        errors.append("category 必须正好包含 no_plate、single_plate、multi_plate 之一")
    elif presence[0] == "no_plate" and len(plates) != 0:
        errors.append("no_plate 时 plates 必须为空")
    elif presence[0] == "single_plate" and len(plates) != 1:
        errors.append("single_plate 时必须正好一块牌")
    elif presence[0] == "multi_plate" and len(plates) < 2:
        errors.append("multi_plate 时至少两块牌")
    if "no_plate" in category and any(tag in category for tag in list(COLOR_TAGS.values()) + list(CONDITION_TAGS) + ["normal"]):
        errors.append("无车牌图像不能再标颜色、倾斜、模糊、反光或 normal")
    for key in CONDITION_TAGS:
        flagged = bool(conditions.get(key))
        if flagged and key not in category:
            errors.append(f"conditions.{key} 为真时 category 要包含 {key}")
        if (not flagged) and key in category:
            errors.append(f"category 含 {key} 时 conditions.{key} 必须为真")
    if "normal" in category:
        if any(conditions.get(key) for key in CONDITION_TAGS) or has_plate is not True:
            errors.append("normal 只用于有车牌且没有倾斜、模糊、反光的图像")
    seen_colors = set()
    plate_ids = set()
    width = record.get("width") if isinstance(record.get("width"), int) else 0
    height = record.get("height") if isinstance(record.get("height"), int) else 0
    for index, plate in enumerate(plates):
        prefix = f"plates[{index}]"
        if not isinstance(plate, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        extra_plate = set(plate) - PLATE_KEYS
        if extra_plate:
            errors.append(f"{prefix} 有未定义字段：" + "、".join(sorted(extra_plate)))
        plate_id = plate.get("plate_id")
        if not isinstance(plate_id, str) or plate_id.strip() == "":
            errors.append(f"{prefix} 缺少 plate_id")
        elif plate_id in plate_ids:
            errors.append(f"plate_id 重复：{plate_id}")
        else:
            plate_ids.add(plate_id)
        box = plate.get("box")
        if not isinstance(box, dict) or set(box) != {"x", "y", "w", "h"}:
            errors.append(f"{prefix}.box 必须正好是 x、y、w、h")
        else:
            if not all(isinstance(box[key], int) for key in ("x", "y", "w", "h")):
                errors.append(f"{prefix}.box 的 x、y、w、h 必须是整数")
            elif box["x"] < 0 or box["y"] < 0 or box["w"] <= 0 or box["h"] <= 0:
                errors.append(f"{prefix}.box 的 x、y 不能为负，w、h 必须为正")
            elif width > 0 and height > 0:
                if box["x"] + box["w"] > width or box["y"] + box["h"] > height:
                    errors.append(f"{prefix}.box 超出图像范围")
        color = METRICS.canon_color(plate.get("color"))
        if "color" not in plate:
            errors.append(f"{prefix} 缺少 color")
        elif color is None:
            errors.append(f"{prefix}.color 不在颜色闭集")
        elif color != "unknown":
            seen_colors.add(color)
        readable = plate.get("readable", True)
        if not isinstance(readable, bool):
            errors.append(f"{prefix}.readable 必须是布尔值")
        number = plate.get("number", "")
        if not isinstance(number, str):
            errors.append(f"{prefix}.number 必须是字符串")
            number = ""
        if readable and number.strip() == "":
            errors.append(f"{prefix} 可读时 number 不能为空")
        if any(ch in number for ch in METRICS.SEPARATORS):
            errors.append(f"{prefix}.number 不要写间隔符，间隔符只允许出现在预测里")
        chars = plate.get("chars")
        count = plate.get("char_count")
        if readable and not isinstance(count, int):
            errors.append(f"{prefix}.char_count 在可读时必须是整数")
        if count is not None and (not isinstance(count, int) or count < 0):
            errors.append(f"{prefix}.char_count 必须是非负整数")
        if chars is not None:
            if not isinstance(chars, list) or not all(isinstance(item, str) and len(item) == 1 for item in chars):
                errors.append(f"{prefix}.chars 必须是单字符数组")
            elif isinstance(count, int) and len(chars) != count:
                errors.append(f"{prefix}.chars 的长度必须等于 char_count")
            elif number and "".join(chars) != number:
                errors.append(f"{prefix}.chars 拼起来必须等于 number")
        if isinstance(count, int) and number and len(number) != count:
            errors.append(f"{prefix}.char_count 必须等于 number 的字符数")
        quad = plate.get("quad")
        if quad is not None:
            if (
                not isinstance(quad, list)
                or len(quad) != 4
                or not all(isinstance(point, dict) and set(point) >= {"x", "y"} for point in quad)
            ):
                errors.append(f"{prefix}.quad 必须是四个 {{x, y}} 点")
            elif width > 0 and height > 0:
                for point in quad:
                    if point["x"] < 0 or point["y"] < 0 or point["x"] > width or point["y"] > height:
                        errors.append(f"{prefix}.quad 有点超出图像范围")
                        break
    expected_tags = {COLOR_TAGS[color] for color in seen_colors}
    actual_tags = {tag for tag in category if tag in COLOR_TAGS.values()}
    if expected_tags != actual_tags:
        errors.append(
            "颜色标签必须与车牌颜色一致，未知颜色不加 color_ 标签："
            f"应为 {sorted(expected_tags)}，实际 {sorted(actual_tags)}"
        )
    return errors


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    pa = abs(estimate - left)
    pb = abs(estimate - up)
    pc = abs(estimate - up_left)
    if pa <= pb and pa <= pc:
        return left
    if pb <= pc:
        return up
    return up_left


def decode_png(data: bytes) -> list[bytearray]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG")
    pos = 8
    width = height = bit_depth = color_type = None
    idat = bytearray()
    palette = None
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        crc = struct.unpack(">I", data[pos + 8 + length : pos + 12 + length])[0]
        if (zlib.crc32(kind + chunk) & 0xFFFFFFFF) != crc:
            raise ValueError("PNG CRC 不正确")
        pos += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, compression, filters, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if compression != 0 or filters != 0:
                raise ValueError("不支持的 PNG 压缩方式")
            if interlace != 0:
                raise ValueError("不支持隔行 PNG")
            if bit_depth != 8:
                raise ValueError("只支持 8 位 PNG")
        elif kind == b"PLTE":
            palette = chunk
        elif kind == b"IDAT":
            idat.extend(chunk)
        elif kind == b"IEND":
            break
    if width is None or color_type is None:
        raise ValueError("PNG 缺少 IHDR")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color_type)
    if channels is None:
        raise ValueError("不支持的 PNG 颜色类型")
    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    rows = []
    cursor = 0
    previous = bytearray(stride)
    for _y in range(height):
        if cursor + 1 + stride > len(raw):
            raise ValueError("PNG 像素数据不完整")
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        if filter_type == 0:
            pass
        elif filter_type == 1:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + left) & 255
        elif filter_type == 2:
            for x in range(stride):
                row[x] = (row[x] + previous[x]) & 255
        elif filter_type == 3:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                row[x] = (row[x] + ((left + previous[x]) // 2)) & 255
        elif filter_type == 4:
            for x in range(stride):
                left = row[x - channels] if x >= channels else 0
                up = previous[x]
                up_left = previous[x - channels] if x >= channels else 0
                row[x] = (row[x] + _paeth(left, up, up_left)) & 255
        else:
            raise ValueError(f"不支持的 PNG 滤波器 {filter_type}")
        previous = row
        rows.append(row)
    if color_type == 3:
        if palette is None:
            raise ValueError("PNG 调色板缺失")
        rgb_rows = []
        for row in rows:
            rgb = bytearray()
            for index in row:
                rgb.extend(palette[index * 3 : index * 3 + 3])
            rgb_rows.append(rgb)
        return rgb_rows
    rgb_rows = []
    for row in rows:
        rgb = bytearray()
        if color_type == 0:
            for value in row:
                rgb.extend((value, value, value))
        elif color_type == 2:
            rgb.extend(row)
        elif color_type == 4:
            for offset in range(0, len(row), 2):
                value = row[offset]
                rgb.extend((value, value, value))
        elif color_type == 6:
            for offset in range(0, len(row), 4):
                rgb.extend(row[offset : offset + 3])
        rgb_rows.append(rgb)
    return rgb_rows


def decode_bmp(data: bytes) -> list[bytearray]:
    if data[:2] != b"BM":
        raise ValueError("不是 BMP")
    pixel_offset = struct.unpack_from("<I", data, 10)[0]
    dib_size = struct.unpack_from("<I", data, 14)[0]
    if dib_size < 40:
        raise ValueError("不支持的 BMP 头")
    width = struct.unpack_from("<i", data, 18)[0]
    height_raw = struct.unpack_from("<i", data, 22)[0]
    planes, bit_count = struct.unpack_from("<HH", data, 26)
    compression = struct.unpack_from("<I", data, 30)[0]
    if planes != 1 or compression != 0:
        raise ValueError("只支持不压缩的 BMP")
    if bit_count != 24:
        raise ValueError("只支持 24 位 BMP")
    top_down = height_raw < 0
    height = abs(height_raw)
    stride = (width * 3 + 3) & ~3
    rows = []
    for y in range(height):
        src_y = y if top_down else height - 1 - y
        start = pixel_offset + src_y * stride
        row = bytearray()
        for x in range(width):
            b, g, r = data[start + x * 3 : start + x * 3 + 3]
            row.extend((r, g, b))
        rows.append(row)
    return rows


def _read_netpbm_tokens(data: bytes):
    text = []
    index = 0
    while index < len(data):
        if data[index] == ord("#"):
            while index < len(data) and data[index] not in (10, 13):
                index += 1
            continue
        if data[index] in b" \t\r\n":
            index += 1
            continue
        start = index
        while index < len(data) and data[index] not in b" \t\r\n#":
            index += 1
        text.append(data[start:index])
    return text


def decode_netpbm(data: bytes) -> list[bytearray]:
    if not data.startswith((b"P3", b"P5", b"P6")):
        raise ValueError("不是 PGM/PPM")
    magic = data[:2]
    if magic == b"P3":
        tokens = _read_netpbm_tokens(data[2:])
        if len(tokens) < 4:
            raise ValueError("PPM 不完整")
        width = int(tokens[0])
        height = int(tokens[1])
        max_value = int(tokens[2])
        values = [int(token) for token in tokens[3:]]
        if max_value <= 0 or len(values) != width * height * 3:
            raise ValueError("PPM 尺寸不正确")
        scale = 255 / max_value
        rows = []
        cursor = 0
        for _y in range(height):
            row = bytearray()
            for _x in range(width):
                row.extend(int(values[cursor + offset] * scale) for offset in range(3))
                cursor += 3
            rows.append(row)
        return rows
    header_end = 2
    tokens = []
    while len(tokens) < 3:
        while header_end < len(data) and data[header_end] in b" \t\r\n":
            header_end += 1
        if header_end < len(data) and data[header_end] == ord("#"):
            while header_end < len(data) and data[header_end] not in (10, 13):
                header_end += 1
            continue
        start = header_end
        while header_end < len(data) and data[header_end] not in b" \t\r\n":
            header_end += 1
        tokens.append(int(data[start:header_end]))
    if header_end >= len(data) or data[header_end] not in b" \t\r\n":
        raise ValueError("PGM/PPM 头不完整")
    header_end += 1
    width, height, max_value = tokens
    channels = 1 if magic == b"P5" else 3
    needed = width * height * channels
    body = data[header_end:]
    if max_value != 255 or len(body) < needed:
        raise ValueError("只支持最大值为 255 的二进制 PGM/PPM")
    rows = []
    cursor = 0
    for _y in range(height):
        row = bytearray()
        for _x in range(width):
            if channels == 1:
                value = body[cursor]
                row.extend((value, value, value))
                cursor += 1
            else:
                row.extend(body[cursor : cursor + 3])
                cursor += 3
        rows.append(row)
    return rows


def decode_image(path: Path, data: bytes) -> list[bytearray]:
    suffix = path.suffix.lower()
    if suffix == ".png" or data.startswith(b"\x89PNG"):
        return decode_png(data)
    if suffix == ".bmp" or data.startswith(b"BM"):
        return decode_bmp(data)
    if suffix in {".ppm", ".pgm"} or data.startswith((b"P3", b"P5", b"P6")):
        return decode_netpbm(data)
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError(f"标准库不能解码 {suffix or '该文件'}，安装 Pillow 后才能做近似重复检查") from exc
    image = Image.open(path).convert("RGB")
    rows = []
    pixels = list(image.getdata())
    width, height = image.size
    for y in range(height):
        row = bytearray()
        for x in range(width):
            r, g, b = pixels[y * width + x]
            row.extend((r, g, b))
        rows.append(row)
    return rows


def average_hash(rows: list[bytearray]) -> str:
    """8×8 平均哈希。灰度是 (R+G+B)//3，位序为从左到右、从上到下。"""
    height = len(rows)
    width = len(rows[0]) // 3
    values = []
    for by in range(8):
        for bx in range(8):
            y0 = by * height // 8
            y1 = max((by + 1) * height // 8, y0 + 1)
            x0 = bx * width // 8
            x1 = max((bx + 1) * width // 8, x0 + 1)
            total = 0
            count = 0
            for y in range(y0, min(y1, height)):
                row = rows[y]
                for x in range(x0, min(x1, width)):
                    offset = x * 3
                    total += (row[offset] + row[offset + 1] + row[offset + 2]) // 3
                    count += 1
            values.append(total / count)
    mean = sum(values) / len(values)
    return "".join("1" if value >= mean else "0" for value in values)


def hamming(left: str, right: str) -> int:
    return sum(a != b for a, b in zip(left, right))


def find_duplicates(entries: list[dict], near_threshold: int) -> dict:
    groups = {}
    for entry in entries:
        groups.setdefault(entry["sha256"], []).append(entry)
    exact = [group for group in groups.values() if len(group) >= 2]
    near = []
    ordered = sorted(entries, key=lambda item: item["path"])
    for index, left in enumerate(ordered):
        if left.get("ahash") is None:
            continue
        for right in ordered[index + 1 :]:
            if right.get("ahash") is None or left["sha256"] == right["sha256"]:
                continue
            distance = hamming(left["ahash"], right["ahash"])
            if distance <= near_threshold:
                near.append({"distance": distance, "left": left, "right": right})
    cross = []
    for group in exact:
        splits = {item.get("split") for item in group}
        if len(splits) > 1:
            cross.append({"kind": "exact", "paths": [item["path"] for item in group], "splits": sorted(splits, key=str)})
    for pair in near:
        left_split = pair["left"].get("split")
        right_split = pair["right"].get("split")
        if left_split != right_split:
            cross.append(
                {
                    "kind": "near",
                    "distance": pair["distance"],
                    "paths": [pair["left"]["path"], pair["right"]["path"]],
                    "splits": sorted({left_split, right_split}, key=str),
                }
            )
    return {"exact": exact, "near": near, "cross_split": cross}


def scan(root: Path, manifest: dict, annotations: list[dict], near_threshold: int) -> dict:
    by_id = {}
    errors = []
    for record in annotations:
        image_id = record.get("image_id")
        if image_id in by_id:
            errors.append(f"标注里 image_id 重复：{image_id}")
        else:
            by_id[image_id] = record
    listed = {}
    for name in SPLITS:
        for image_id in manifest.get("splits", {}).get(name, []):
            listed[image_id] = name
            if image_id not in by_id:
                errors.append(f"清单中的 {image_id} 没有标注")
    for image_id, record in by_id.items():
        if image_id not in listed:
            errors.append(f"标注 {image_id} 不在清单里")
        elif record.get("purpose") != listed[image_id]:
            errors.append(f"{image_id} 的 purpose 与清单划分不一致")
    paths = {}
    for image_id, record in by_id.items():
        relative = str(record.get("relative_path", "")).replace("\\", "/")
        paths[relative] = {
            "image_id": image_id,
            "split": listed.get(image_id) or record.get("purpose"),
        }
    raw_root = root / "data" / "raw"
    if raw_root.is_dir():
        for path in raw_root.rglob("*"):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            relative = path.relative_to(root).as_posix()
            split = None
            parts = path.relative_to(raw_root).parts
            if parts and parts[0] in SPLITS:
                split = parts[0]
            paths.setdefault(relative, {"image_id": None, "split": split})
    entries = []
    unreadable = []
    for relative, meta in sorted(paths.items()):
        path = root / relative
        if not path.is_file():
            errors.append(f"标注指向的文件不存在：{relative}")
            continue
        data = path.read_bytes()
        entry = {
            "image_id": meta["image_id"],
            "path": relative,
            "split": meta["split"],
            "sha256": sha256_bytes(data),
            "ahash": None,
        }
        try:
            entry["ahash"] = average_hash(decode_image(path, data))
        except Exception as exc:
            unreadable.append({"path": relative, "reason": str(exc)})
        entries.append(entry)
    report = find_duplicates(entries, near_threshold)
    report["errors"] = errors
    report["unreadable"] = unreadable
    report["n_images"] = len(entries)
    report["near_threshold"] = near_threshold
    return report


def format_report(report: dict) -> str:
    lines = [f"检查了 {report['n_images']} 张图像。近似重复阈值：汉明距离 <= {report['near_threshold']}。"]
    if report["n_images"] == 0:
        lines.append("当前没有样本。完全重复和近似重复都没有对象。")
    if report["errors"]:
        lines.append("结构问题：")
        lines.extend(f"- {item}" for item in report["errors"])
    if not report["exact"] and not report["near"] and report["n_images"]:
        lines.append("没有发现完全重复或近似重复。")
    for group in report["exact"]:
        rendered = ", ".join(item["path"] for item in group)
        lines.append(f"完全重复：{rendered}")
    for pair in report["near"]:
        lines.append(
            f"近似重复：距离 {pair['distance']}，{pair['left']['path']} 与 {pair['right']['path']}"
        )
    for item in report["cross_split"]:
        lines.append(f"跨划分重复（{item['kind']}）：{', '.join(item['paths'])}，划分 {item['splits']}")
    for item in report["unreadable"]:
        lines.append(f"未能计算近似哈希：{item['path']}（{item['reason']}）")
    return "\n".join(lines)


def report_failed(report: dict) -> bool:
    return bool(report["errors"] or report["exact"] or report["near"] or report["unreadable"])


def _write_bmp(path: Path, rows: list[bytearray]) -> None:
    height = len(rows)
    width = len(rows[0]) // 3
    stride = (width * 3 + 3) & ~3
    pixel_size = stride * height
    header = struct.pack("<2sIHHI", b"BM", 54 + pixel_size, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0, pixel_size, 2835, 2835, 0, 0)
    body = bytearray()
    for row in reversed(rows):
        bgr = bytearray()
        for offset in range(0, len(row), 3):
            r, g, b = row[offset : offset + 3]
            bgr.extend((b, g, r))
        bgr.extend(b"\x00" * (stride - width * 3))
        body.extend(bgr)
    path.write_bytes(header + info + body)


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _write_png(path: Path, rows: list[bytearray], filter_type: int = 0) -> None:
    height = len(rows)
    width = len(rows[0]) // 3
    raw = bytearray()
    previous = bytearray(width * 3)
    for row in rows:
        filtered = bytearray(row)
        if filter_type == 1:
            for x in range(len(row)):
                left = row[x - 3] if x >= 3 else 0
                filtered[x] = (row[x] - left) & 255
        elif filter_type == 2:
            for x in range(len(row)):
                filtered[x] = (row[x] - previous[x]) & 255
        elif filter_type == 3:
            for x in range(len(row)):
                left = row[x - 3] if x >= 3 else 0
                filtered[x] = (row[x] - ((left + previous[x]) // 2)) & 255
        elif filter_type == 4:
            for x in range(len(row)):
                left = row[x - 3] if x >= 3 else 0
                up = previous[x]
                up_left = previous[x - 3] if x >= 3 else 0
                filtered[x] = (row[x] - _paeth(left, up, up_left)) & 255
        raw.append(filter_type)
        raw.extend(filtered)
        previous = bytearray(row)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(bytes(raw)))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def _solid_rows(width: int, height: int, painter) -> list[bytearray]:
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            row.extend(painter(x, y))
        rows.append(row)
    return rows


def self_test() -> int:
    failures = []
    manifest = load_json(ROOT / "data" / "splits" / "manifest.json")
    manifest_errors = validate_manifest(manifest)
    if manifest_errors:
        failures.append("空清单未通过：" + "；".join(manifest_errors))
    if any(manifest["splits"][name] for name in SPLITS):
        failures.append("提交的清单应为空模板")
    examples = load_json(ROOT / "data" / "schema" / "examples.json")
    seen_tags = set()
    purposes = set()
    unknown = False
    for record in examples:
        problems = validate_annotation(record, allow_example=True)
        if problems:
            failures.append(f"{record.get('image_id')} 示例不合法：{'；'.join(problems)}")
        seen_tags.update(record.get("category") or [])
        purposes.add(record.get("purpose"))
        for plate in record.get("plates") or []:
            if METRICS.canon_color(plate.get("color")) == "unknown":
                unknown = True
    required = {
        "no_plate",
        "single_plate",
        "multi_plate",
        "tilt",
        "blur",
        "glare",
        "color_blue",
        "color_yellow",
        "color_green",
        "color_white",
        "color_black",
    }
    if not required <= seen_tags:
        failures.append(f"示例缺少情形：{sorted(required - seen_tags)}")
    if purposes != set(SPLITS):
        failures.append("示例没有覆盖四个划分")
    if not unknown:
        failures.append("示例没有显式未知颜色")
    bad = {
        "image_id": "bad",
        "relative_path": "data/raw/development/bad.jpg",
        "width": 10,
        "height": 10,
        "source": {"origin": "synthetic", "name": "x", "license": "none"},
        "purpose": "development",
        "category": ["no_plate"],
        "has_plate": True,
        "plates": [],
        "conditions": {"tilt": False, "blur": False, "glare": False},
    }
    if not validate_annotation(bad):
        failures.append("has_plate 与空 plates 的矛盾没有被抓住")
    overlapped = json.loads(json.dumps(manifest))
    overlapped["splits"]["library"].append("same")
    overlapped["splits"]["final_test"].append("same")
    if not any("同时出现" in item for item in validate_manifest(overlapped)):
        failures.append("跨划分的同一个 image_id 没有被抓住")

    vertical = _solid_rows(32, 32, lambda x, _y: (0, 0, 0) if x < 16 else (255, 255, 255))
    near = [bytearray(row) for row in vertical]
    near[0][16 * 3] = 0
    horizontal = _solid_rows(32, 32, lambda _x, y: (0, 0, 0) if y < 16 else (255, 255, 255))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        a = root / "a.bmp"
        a_copy = root / "a_copy.bmp"
        a_near = root / "a_near.bmp"
        b = root / "b.bmp"
        a_png = root / "a.png"
        _write_bmp(a, vertical)
        _write_bmp(a_copy, vertical)
        _write_bmp(a_near, near)
        _write_bmp(b, horizontal)
        _write_png(a_png, vertical, 0)
        decoded = decode_bmp(a.read_bytes())
        if decoded[0][:3] != bytearray((0, 0, 0)) or decoded[0][16 * 3 : 16 * 3 + 3] != bytearray((255, 255, 255)):
            failures.append("BMP 往返后像素不对")
        tiny = _solid_rows(
            2,
            2,
            lambda x, y: [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)][y * 2 + x],
        )
        for filter_type in (0, 1, 2, 3, 4):
            png_path = root / f"f{filter_type}.png"
            _write_png(png_path, tiny, filter_type)
            if decode_png(png_path.read_bytes()) != tiny:
                failures.append(f"PNG 滤波器 {filter_type} 解码不对")
        entries = []
        for path, split in (
            (a, "library"),
            (a_copy, "library"),
            (a_near, "final_test"),
            (b, "development"),
            (a_png, "library"),
        ):
            data = path.read_bytes()
            entries.append(
                {
                    "path": path.name,
                    "split": split,
                    "sha256": sha256_bytes(data),
                    "ahash": average_hash(decode_image(path, data)),
                }
            )
        found = find_duplicates(entries, NEAR_HAMMING_THRESHOLD)
        exact_paths = {tuple(sorted(item["path"] for item in group)) for group in found["exact"]}
        if ("a.bmp", "a_copy.bmp") not in exact_paths:
            failures.append("完全相同的 BMP 没有报成完全重复")
        near_pairs = {
            tuple(sorted((pair["left"]["path"], pair["right"]["path"]))) for pair in found["near"]
        }
        if ("a.bmp", "a_near.bmp") not in near_pairs:
            failures.append("改了一个像素的图没有报成近似重复")
        if ("a.bmp", "a.png") not in near_pairs:
            failures.append("同样像素的 PNG 和 BMP 没有报成近似重复")
        if any("b.bmp" in pair and "a.bmp" in pair for pair in near_pairs):
            failures.append("左右分割和上下分割被误报成近似重复")
        if not any(set(item["splits"]) == {"final_test", "library"} for item in found["cross_split"]):
            failures.append("字符库和终测之间的近似重复没有标成跨划分")
    if failures:
        print("自检失败：", file=sys.stderr)
        for item in failures:
            print(f"- {item}", file=sys.stderr)
        return 1
    print("自检通过")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查数据清单、标注和重复图像。")
    parser.add_argument("--self-test", action="store_true", help="检查模板并用合成色块验证重复检测")
    parser.add_argument("--manifest", default=str(ROOT / "data" / "splits" / "manifest.json"))
    parser.add_argument("--annotations", default=str(ROOT / "data" / "annotations" / "annotations.jsonl"))
    parser.add_argument("--near-threshold", type=int, default=NEAR_HAMMING_THRESHOLD)
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        return self_test()
    manifest = load_json(Path(args.manifest))
    errors = validate_manifest(manifest)
    annotations = load_jsonl(Path(args.annotations))
    for record in annotations:
        for problem in validate_annotation(record, allow_example=False):
            errors.append(f"{record.get('image_id')}: {problem}")
    report = scan(ROOT, manifest, annotations, args.near_threshold)
    report["errors"] = errors + report["errors"]
    if args.json:
        printable = {
            "n_images": report["n_images"],
            "near_threshold": report["near_threshold"],
            "errors": report["errors"],
            "unreadable": report["unreadable"],
            "exact": [[item["path"] for item in group] for group in report["exact"]],
            "near": [
                {
                    "distance": pair["distance"],
                    "paths": [pair["left"]["path"], pair["right"]["path"]],
                }
                for pair in report["near"]
            ],
            "cross_split": report["cross_split"],
        }
        print(json.dumps(printable, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 1 if report_failed(report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
