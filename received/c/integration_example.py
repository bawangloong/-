"""B -> C -> D 的实际接口示例；B 源代码原样保存在 integration/B_original。"""

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image

from char_features import read_image, write_image
from recognize_chars import CharacterRecognizer, natural_key
from visualize_matches import save_match_sheet

ROOT = Path(__file__).resolve().parent
DEFAULT_B = ROOT / "integration/B_original"


def load_module(path, name):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"缺少 B 的模块 {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recognize_b_result(segmentation, recognizer):
    """最小适配接口：不改 B 切片，不根据文件名或期望答案修正输出。"""
    if not isinstance(segmentation, dict) or not isinstance(segmentation.get("chars"), (list, tuple)):
        raise ValueError("B 结果须包含 chars 列表")
    chars = segmentation["chars"]
    if segmentation.get("count", len(chars)) != len(chars):
        raise ValueError("B 的 count 与实际切片数不一致")
    result = recognizer.recognize_chars(chars)
    result["segmentation_status"] = segmentation.get("status", "unknown")
    if result["segmentation_status"] != "ok":
        result["warnings"].append("B 的分割状态异常，请先检查切片或让 A 矫正车牌")
    return result


class BToC:
    """GUI 初始化一次复用。输入彩色图须为 RGB uint8；cv2 输入先 BGR -> RGB。"""

    def __init__(self, b_dir=DEFAULT_B, library=None):
        self.b_dir = Path(b_dir)
        self.color_module = load_module(self.b_dir / "plate_color.py", "_plate_b_color")
        self.segment_module = load_module(self.b_dir / "segment_chars.py", "_plate_b_segment")
        self.recognizer = CharacterRecognizer(library)

    def run(self, plate_rgb):
        array = np.asarray(plate_rgb)
        if array.dtype != np.uint8 or array.ndim != 3 or array.shape[2] != 3 or min(array.shape[:2]) < 2:
            raise ValueError("BToC.run 需要 H×W×3 RGB uint8 图像")
        color = self.color_module.classify_plate_color(array)
        prefer_dark = None if color["color"] == "unknown" else self.color_module.is_dark_text_on_light_plate(color["color"])
        segmentation = self.segment_module.segment_plate(array, prefer_dark_text=prefer_dark, debug=True)
        recognition = recognize_b_result(segmentation, self.recognizer)
        public = {
            "color": color,
            "segmentation": {"count": segmentation["count"], "status": segmentation["status"], "boxes": segmentation["boxes"],
                             "box_coordinates": "B stage norm image (height 140), not original image coordinates"},
            "recognition": recognition,
        }
        return public, segmentation


def synthetic_truth(b_dir):
    """仅评估读真值；识别链路完全不读 SPECS。"""
    file = Path(b_dir) / "make_test_plates.py"
    if not file.is_file():
        return {}
    for node in ast.parse(file.read_text(encoding="utf-8-sig")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SPECS" for t in node.targets):
            return {spec[0]: spec[3].replace("·", "") for spec in ast.literal_eval(node.value)}
    return {}


def run_demo(b_dir=DEFAULT_B, output=None, image=None):
    b_dir = Path(b_dir)
    output = Path(output) if output else ROOT / "results/B_integration"
    output.mkdir(parents=True, exist_ok=True)
    bridge = BToC(b_dir)
    files = [Path(image)] if image else sorted((b_dir / "samples").glob("*.png"))
    if not files:
        raise ValueError("未找到 B 的输入车牌图片")
    truth = synthetic_truth(b_dir)
    summary = []
    for path in files:
        rgb = np.asarray(Image.open(path).convert("RGB"))
        result, segmentation = bridge.run(rgb)
        cut_dir = output / (path.stem + "_chars")
        for position, char in enumerate(segmentation["chars"], 1):
            write_image(cut_dir / f"char_{position:02}.png", char)
        result["source"] = path.name
        is_b_sample = path.resolve() == (b_dir / "samples" / path.name).resolve()
        expected = truth.get(path.name) if is_b_sample else None
        result["evaluation_only"] = {"truth": expected, "source": "B make_test_plates.py SPECS (synthetic)" if is_b_sample else "user input; no truth supplied",
                                     "exact_match": result["recognition"]["text"] == expected if expected else None}
        archived = b_dir / "output" / (path.stem + "_chars")
        archived_files = sorted(archived.glob("*.png"), key=natural_key)
        if archived_files:
            result["archived_slice_comparison"] = {
                "same_count": len(archived_files) == len(segmentation["chars"]),
                "all_pixels_equal": len(archived_files) == len(segmentation["chars"]) and all(
                    np.array_equal(read_image(p), char) for p, char in zip(archived_files, segmentation["chars"]))}
        (output / (path.stem + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        chars = segmentation["chars"]
        # 数量异常时仅展示 unrestricted 候选作诊断；不将其冒充整牌输出。
        display = result["recognition"]["characters"]
        if not display and chars:
            display = bridge.recognizer.recognize_chars(chars, layout="unrestricted")["characters"]
        save_match_sheet(chars, display, bridge.recognizer, output / (path.stem + "_matches.png"),
                         path.name + " / B 分割后匹配")
        row = {"file": path.name, "truth": expected, "color": result["color"]["color"],
               "count": segmentation["count"], "segmentation_status": segmentation["status"],
               "prediction": result["recognition"]["text"], "status": result["recognition"]["status"],
               "exact_match": result["evaluation_only"]["exact_match"]}
        if expected and len(expected) == len(result["recognition"]["text"]):
            row["correct_characters"] = sum(a == b for a, b in zip(expected, result["recognition"]["text"]))
        else:
            row["correct_characters"] = None
        summary.append(row)
    with (output / "summary.csv").open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    stats = {"dataset": "B synthetic samples, not real-world plate benchmark", "images": len(summary),
             "truth_available": sum(row["truth"] is not None for row in summary),
             "exact_matches": sum(row["exact_match"] is True for row in summary),
             "abnormal_segmentation": sum(row["segmentation_status"] != "ok" for row in summary), "rows": summary}
    (output / "summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b-dir", type=Path, default=DEFAULT_B)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--image", type=Path, help="A 提供的单块已矫正车牌；默认跑 B 的合成样例")
    args = parser.parse_args()
    run_demo(args.b_dir, args.output, args.image)
