"""生成完整 65 类字体辅助模板。仅首次准备需要本机字体，不读取 B 数据或答案。"""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from char_features import normalize_character
from labels import ALL_LABELS, LABEL_TO_FOLDER

ROOT = Path(__file__).resolve().parent


def generate():
    manifest = ROOT / "font_samples_manifest.csv"
    if manifest.exists():
        raise ValueError("字体模板已经生成；日常使用无需重跑")
    fonts = [Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")]
    records = []
    known = set()
    for path in fonts:
        if not path.is_file():
            continue
        for size in [48, 64, 80]:
            face = ImageFont.truetype(str(path), size)
            for label in ALL_LABELS:
                box = face.getbbox(label)
                source = Image.new("L", (box[2] - box[0] + 8, box[3] - box[1] + 8), 0)
                ImageDraw.Draw(source).text((4 - box[0], 4 - box[1]), label, font=face, fill=255)
                # 仿照切片接口的固定画布做一次缩放，适配小字符的采样效应。
                binary = np.asarray(source) > 127
                ys, xs = np.nonzero(binary)
                glyph = Image.fromarray(binary[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8) * 255)
                scale = min(36 / glyph.height, 16 / glyph.width)
                glyph = glyph.resize((max(1, int(glyph.width * scale)), max(1, int(glyph.height * scale))), Image.Resampling.LANCZOS)
                cut = Image.new("L", (20, 40), 0)
                cut.paste(glyph, ((20 - glyph.width) // 2, (40 - glyph.height) // 2))
                normalized = normalize_character(np.asarray(cut))
                digest = hashlib.sha256(normalized.tobytes()).hexdigest()
                if digest in known:
                    continue
                known.add(digest)
                relative = Path("character_library/train") / LABEL_TO_FOLDER[label] / f"font_{path.stem}_{size}.png"
                target = ROOT / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                cut.save(target)
                records.append({"file": relative.as_posix(), "label": label, "font": path.name,
                                "font_size": size, "split": "train_synthetic", "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                                "normalized_sha256": digest})
    if not records:
        raise ValueError("未找到指定字体；交付包已附模板，日常无需本机字体")
    with manifest.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    note = {"count": len(records), "labels": len(set(row["label"] for row in records)),
            "fonts": [p.name for p in fonts if p.is_file()], "sizes": [48, 64, 80],
            "source": "rendered independently for every supported label, not B slices or B expected plate strings",
            "purpose": "auxiliary templates for screen-font inputs; same-font synthetic evaluation is not unseen-font generalization",
            "font_notice": "font binaries are NOT redistributed; rendered course-use samples only"}
    (ROOT / "font_samples_summary.json").write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(note, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    generate()
