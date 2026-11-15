"""车牌评测的纯计算。

口径以 eval/README.md 为准。这里不读图像，也不调用检测或识别。
"""

from __future__ import annotations

import math

# 颜色闭集。比较前先归一化；只有显式未知才是 unknown。
COLOR_LABELS = ("blue", "yellow", "green", "white", "black", "unknown")

COLOR_ALIASES = {
    "blue": "blue",
    "蓝": "blue",
    "蓝色": "blue",
    "蓝牌": "blue",
    "yellow": "yellow",
    "黄": "yellow",
    "黄色": "yellow",
    "黄牌": "yellow",
    "green": "green",
    "绿": "green",
    "绿色": "green",
    "绿牌": "green",
    "新能源": "green",
    "新能源绿": "green",
    "white": "white",
    "白": "white",
    "白色": "white",
    "白牌": "white",
    "black": "black",
    "黑": "black",
    "黑色": "black",
    "黑牌": "black",
    "unknown": "unknown",
    "未知": "unknown",
    "无法判断": "unknown",
}

SPLITS = ("development", "library", "validation", "final_test")

# 整牌比较前删掉的间隔符。汉字和数字保留。
SEPARATORS = set(" \t\r\n·•・.-—_/．。")

DEFAULT_IOU_THRESHOLD = 0.5


def canon_color(value) -> str | None:
    """返回闭集中的颜色。缺字段、空串和闭集外的词都返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if text in COLOR_ALIASES:
        return COLOR_ALIASES[text]
    lowered = text.lower()
    if lowered in COLOR_ALIASES:
        return COLOR_ALIASES[lowered]
    return None


def normalize_plate(value) -> str:
    """去掉间隔符，并把拉丁字母改成大写。"""
    if value is None:
        return ""
    out = []
    for ch in str(value):
        if ch in SEPARATORS:
            continue
        if "a" <= ch <= "z":
            ch = ch.upper()
        out.append(ch)
    return "".join(out)


def char_sequence(plate: dict | None) -> list[str]:
    """从左到右的字符序列。有 chars 时用 chars，否则拆号码。"""
    if not plate:
        return []
    if "chars" in plate and isinstance(plate.get("chars"), list):
        seq: list[str] = []
        for item in plate["chars"]:
            seq.extend(list(normalize_plate(item)))
        return seq
    return list(normalize_plate(plate.get("number")))


def plate_string(plate: dict | None) -> str:
    """整牌字符串。有 number 时用 number，没有时才拼接 chars。"""
    if not plate:
        return ""
    if "number" in plate and plate.get("number") is not None:
        return normalize_plate(plate.get("number"))
    return "".join(char_sequence(plate))


def stated_count(plate: dict) -> int:
    """字符数。有 char_count 就用它，否则用字符序列长度。"""
    if "char_count" in plate and plate["char_count"] is not None:
        return int(plate["char_count"])
    return len(char_sequence(plate))


def parse_box(box) -> tuple[float, float, float, float]:
    """解析原图坐标框，返回 x, y, w, h。"""
    if isinstance(box, dict):
        try:
            x = box["x"]
            y = box["y"]
        except KeyError as exc:
            raise ValueError(f"框缺少字段 {exc.args[0]}") from exc
        if "w" in box:
            w = box["w"]
        elif "width" in box:
            w = box["width"]
        else:
            raise ValueError("框缺少字段 w")
        if "h" in box:
            h = box["h"]
        elif "height" in box:
            h = box["height"]
        else:
            raise ValueError("框缺少字段 h")
    elif isinstance(box, (list, tuple)) and len(box) == 4:
        x, y, w, h = box
    else:
        raise ValueError("框必须是 {x, y, w, h} 或长度为 4 的列表")
    return float(x), float(y), float(w), float(h)


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """轴对齐框的交并比。边只相接、没有面积重叠时为 0。"""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    if aw <= 0 or ah <= 0 or bw <= 0 or bh <= 0:
        return 0.0
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    inter_w = x2 - x1
    inter_h = y2 - y1
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    if union <= 0:
        return 0.0
    return inter / union


def match_plates(gt_plates: list[dict], pred_plates: list[dict], iou_threshold: float):
    """同一张图内按 IoU 贪心一对一配对。

    只保留 IoU >= 阈值的候选。排序键是 IoU 降序、标注下标升序、预测下标升序。
    返回 (配对列表, 未配上的预测下标, 未配上的标注下标)。
    配对元素是 (gt_index, pred_index, iou)。
    """
    gt_boxes = [parse_box(plate["box"]) for plate in gt_plates]
    pred_boxes = [parse_box(plate["box"]) for plate in pred_plates]
    candidates = []
    for gi, gt_box in enumerate(gt_boxes):
        for pi, pred_box in enumerate(pred_boxes):
            value = iou(gt_box, pred_box)
            if value >= iou_threshold:
                candidates.append((value, gi, pi))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
    used_gt = set()
    used_pred = set()
    matches = []
    for value, gi, pi in candidates:
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        matches.append((gi, pi, value))
    false_pos = [pi for pi in range(len(pred_plates)) if pi not in used_pred]
    false_neg = [gi for gi in range(len(gt_plates)) if gi not in used_gt]
    return matches, false_pos, false_neg


def _counter():
    return {"correct": 0, "total": 0}


def _mark(counter: dict, ok: bool) -> None:
    counter["total"] += 1
    if ok:
        counter["correct"] += 1


def _char_hits(gt_plate: dict, pred_plate: dict | None) -> tuple[int, int]:
    gt_seq = char_sequence(gt_plate)
    pred_seq = char_sequence(pred_plate)
    correct = 0
    for index, ch in enumerate(gt_seq):
        if index < len(pred_seq) and pred_seq[index] == ch:
            correct += 1
    return correct, len(gt_seq)


def gt_present(gt: dict) -> bool:
    if "has_plate" in gt:
        return bool(gt["has_plate"])
    return len(gt.get("plates") or []) > 0


def has_scorable_text(plate: dict) -> bool:
    return plate_string(plate) != ""


def score_images(images: list[dict], iou_threshold: float) -> dict:
    """汇总一批图像。

    每项需要 image_id、gt、pred。pred 为 None 或带 error 的项只计入错误数，
    不进入各准确率的分母。elapsed_s 可缺。
    """
    presence = _counter()
    color = _counter()
    count = _counter()
    char_on_hits = _counter()
    char_e2e = _counter()
    plate_on_hits = _counter()
    plate_e2e = _counter()
    tp = fp = fn = 0
    n_gt = 0
    n_pred = 0
    n_errors = 0
    elapsed = []
    details = []

    for image in images:
        image_id = image.get("image_id")
        if image.get("error") or image.get("pred") is None:
            n_errors += 1
            details.append({"image_id": image_id, "error": image.get("error") or "missing prediction"})
            continue
        gt = image["gt"]
        pred = image["pred"]
        gt_plates = list(gt.get("plates") or [])
        pred_plates = list(pred.get("plates") or [])
        matches, false_pos, false_neg = match_plates(gt_plates, pred_plates, iou_threshold)
        tp += len(matches)
        fp += len(false_pos)
        fn += len(false_neg)
        n_gt += len(gt_plates)
        n_pred += len(pred_plates)
        presence_ok = gt_present(gt) == (len(pred_plates) > 0)
        _mark(presence, presence_ok)

        matched_gt = set()
        for gi, pi, _value in matches:
            matched_gt.add(gi)
            gt_plate = gt_plates[gi]
            pred_plate = pred_plates[pi]
            gt_color = canon_color(gt_plate.get("color"))
            pred_color = canon_color(pred_plate.get("color"))
            _mark(color, gt_color is not None and gt_color == pred_color)
            if gt_plate.get("char_count") is not None:
                _mark(count, stated_count(pred_plate) == int(gt_plate["char_count"]))
            if has_scorable_text(gt_plate):
                correct, total = _char_hits(gt_plate, pred_plate)
                char_on_hits["correct"] += correct
                char_on_hits["total"] += total
                char_e2e["correct"] += correct
                char_e2e["total"] += total
                strings_equal = plate_string(gt_plate) == plate_string(pred_plate)
                _mark(plate_on_hits, strings_equal)
                _mark(plate_e2e, strings_equal)

        for gi in false_neg:
            gt_plate = gt_plates[gi]
            if has_scorable_text(gt_plate):
                _correct, total = _char_hits(gt_plate, None)
                char_e2e["total"] += total
                _mark(plate_e2e, False)

        if image.get("elapsed_s") is not None:
            elapsed.append(float(image["elapsed_s"]))
        details.append(
            {
                "image_id": image_id,
                "presence_correct": presence_ok,
                "tp": len(matches),
                "fp": len(false_pos),
                "fn": len(false_neg),
            }
        )

    return {
        "n_images": presence["total"],
        "n_errors": n_errors,
        "n_gt_plates": n_gt,
        "n_pred_plates": n_pred,
        "plate_presence": presence,
        "localization": {"tp": tp, "fp": fp, "fn": fn},
        "color": color,
        "char_count": count,
        "character_on_hits": char_on_hits,
        "character_end_to_end": char_e2e,
        "full_plate_on_hits": plate_on_hits,
        "full_plate_end_to_end": plate_e2e,
        "elapsed_s": elapsed,
        "images": details,
    }


def _rate(correct: int, total: int):
    if total == 0:
        return None
    return correct / total


def median(values: list[float]):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def percentile_nearest_rank(values: list[float], percent: float):
    """最近秩百分位。下标 = ceil(percent/100 * n) - 1。"""
    if not values:
        return None
    ordered = sorted(values)
    rank = math.ceil(percent / 100.0 * len(ordered)) - 1
    rank = min(max(rank, 0), len(ordered) - 1)
    return ordered[rank]


def public_report(raw: dict, iou_threshold: float, kind: str) -> dict:
    elapsed = raw["elapsed_s"]
    measured = kind == "system-evaluation"
    return {
        "kind": kind,
        "is_system_measurement": measured,
        "definitions": "eval/README.md",
        "iou_threshold": iou_threshold,
        "n_images": raw["n_images"],
        "n_errors": raw["n_errors"],
        "n_gt_plates": raw["n_gt_plates"],
        "n_pred_plates": raw["n_pred_plates"],
        "plate_presence": {
            "correct": raw["plate_presence"]["correct"],
            "total": raw["plate_presence"]["total"],
            "accuracy": _rate(raw["plate_presence"]["correct"], raw["plate_presence"]["total"]),
        },
        "localization": {
            "tp": raw["localization"]["tp"],
            "fp": raw["localization"]["fp"],
            "fn": raw["localization"]["fn"],
            "precision": _rate(
                raw["localization"]["tp"],
                raw["localization"]["tp"] + raw["localization"]["fp"],
            ),
            "recall": _rate(
                raw["localization"]["tp"],
                raw["localization"]["tp"] + raw["localization"]["fn"],
            ),
            "iou_threshold": iou_threshold,
        },
        "color": {
            "correct": raw["color"]["correct"],
            "total": raw["color"]["total"],
            "accuracy": _rate(raw["color"]["correct"], raw["color"]["total"]),
            "label_set": list(COLOR_LABELS),
        },
        "char_count": {
            "correct": raw["char_count"]["correct"],
            "total": raw["char_count"]["total"],
            "accuracy": _rate(raw["char_count"]["correct"], raw["char_count"]["total"]),
        },
        "character": {
            "on_hits": {
                "correct": raw["character_on_hits"]["correct"],
                "total": raw["character_on_hits"]["total"],
                "accuracy": _rate(
                    raw["character_on_hits"]["correct"], raw["character_on_hits"]["total"]
                ),
            },
            "end_to_end": {
                "correct": raw["character_end_to_end"]["correct"],
                "total": raw["character_end_to_end"]["total"],
                "accuracy": _rate(
                    raw["character_end_to_end"]["correct"],
                    raw["character_end_to_end"]["total"],
                ),
            },
        },
        "full_plate": {
            "on_hits": {
                "correct": raw["full_plate_on_hits"]["correct"],
                "total": raw["full_plate_on_hits"]["total"],
                "accuracy": _rate(
                    raw["full_plate_on_hits"]["correct"], raw["full_plate_on_hits"]["total"]
                ),
            },
            "end_to_end": {
                "correct": raw["full_plate_end_to_end"]["correct"],
                "total": raw["full_plate_end_to_end"]["total"],
                "accuracy": _rate(
                    raw["full_plate_end_to_end"]["correct"],
                    raw["full_plate_end_to_end"]["total"],
                ),
            },
        },
        "runtime": {
            "n_timed": len(elapsed),
            "total_s": None if not elapsed else sum(elapsed),
            "mean_s": None if not elapsed else sum(elapsed) / len(elapsed),
            "median_s": median(elapsed),
            "p95_s": percentile_nearest_rank(elapsed, 95),
            "timer": "time.perf_counter around one pipeline.run(image_path) call per image",
        },
        "images": raw["images"],
    }


def summary_lines(report: dict) -> list[str]:
    """中文摘要。分子分母是计数，不是实测结论。"""
    loc = report["localization"]
    lines = [
        f"图像 {report['n_images']}，调用错误 {report['n_errors']}",
        f"标注车牌 {report['n_gt_plates']}，预测车牌 {report['n_pred_plates']}",
        _fraction("车牌是否存在", report["plate_presence"]),
        (
            f"定位 TP/FP/FN {loc['tp']}/{loc['fp']}/{loc['fn']}"
            f"（IoU>={report['iou_threshold']}）"
        ),
        _fraction("颜色", report["color"]),
        _fraction("字符数量", report["char_count"]),
        _fraction("字符识别（定位命中后）", report["character"]["on_hits"]),
        _fraction("字符识别（端到端）", report["character"]["end_to_end"]),
        _fraction("整牌（定位命中后）", report["full_plate"]["on_hits"]),
        _fraction("整牌（端到端）", report["full_plate"]["end_to_end"]),
    ]
    runtime = report["runtime"]
    timing_name = "运行时间" if report.get("is_system_measurement") else "夹具计时（不是系统运行时间）"
    if runtime["n_timed"]:
        lines.append(
            f"{timing_name} {runtime['n_timed']} 张，平均 {runtime['mean_s']:.6f} 秒，"
            f"中位数 {runtime['median_s']:.6f} 秒，p95 {runtime['p95_s']:.6f} 秒"
        )
    else:
        lines.append(f"{timing_name} 无")
    return lines


def _fraction(name: str, counter: dict) -> str:
    return f"{name} {counter['correct']}/{counter['total']}"
