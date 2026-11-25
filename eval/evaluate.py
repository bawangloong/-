"""按固定清单评测车牌流水线。

没有 pipeline.py 时直接退出，不编造识别结果。
--fixture 只用合成对照检查指标算术，那个结果不能写进实验报告。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

from metrics import (
    DEFAULT_IOU_THRESHOLD,
    SPLITS,
    canon_color,
    char_sequence,
    has_scorable_text,
    iou,
    match_plates,
    median,
    parse_box,
    percentile_nearest_rank,
    plate_string,
    public_report,
    score_images,
    stated_count,
    summary_lines,
)

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_NAME = "pipeline.py"
COUNT_FIELDS = (
    "plate_presence",
    "localization",
    "color",
    "char_count",
    "character_on_hits",
    "character_end_to_end",
    "full_plate_on_hits",
    "full_plate_end_to_end",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> dict[str, dict]:
    records = {}
    if not path.is_file():
        return records
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        record = json.loads(text)
        image_id = record.get("image_id")
        if not image_id:
            raise SystemExit(f"{path}:{line_no} 缺少 image_id")
        if image_id in records:
            raise SystemExit(f"标注里 image_id 重复：{image_id}")
        records[image_id] = record
    return records


def selected_ids(manifest: dict, splits: list[str]) -> list[str]:
    unknown = [name for name in splits if name not in SPLITS]
    if unknown:
        raise SystemExit(f"未知划分：{', '.join(unknown)}。只能是 {', '.join(SPLITS)}")
    seen = set()
    for name, ids in manifest.get("splits", {}).items():
        for image_id in ids:
            if image_id in seen:
                raise SystemExit(f"image_id 出现在多个划分：{image_id}")
            seen.add(image_id)
    chosen = []
    for name in splits:
        for image_id in manifest.get("splits", {}).get(name, []):
            chosen.append(image_id)
    return chosen


def pipeline_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return ROOT / PIPELINE_NAME


def load_pipeline(path: Path):
    if not path.is_file():
        looked = path
        print(
            "pipeline missing: "
            f"未找到角色 D 的 pipeline.py（查找位置：{looked}）。\n"
            "evaluate.py 只按清单评测，流水线不在时不会编造识别结果。\n"
            "请把 pipeline.py 放到仓库根目录，或用 --pipeline 指向它。\n"
            "调用约定写在 eval/README.md：run(image_path) -> {\"plates\": [...]}。",
            file=sys.stderr,
        )
        raise SystemExit(2)
    spec = importlib.util.spec_from_file_location("plate_pipeline", path)
    if spec is None or spec.loader is None:
        print(f"找到了 {path}，但无法加载。这不是 pipeline missing。", file=sys.stderr)
        raise SystemExit(3)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        print(f"找到了 {path}，但导入失败。这不是 pipeline missing。\n{exc}", file=sys.stderr)
        raise SystemExit(3) from exc
    run = getattr(module, "run", None)
    if not callable(run):
        print(
            f"找到了 {path}，但没有可调用的 run(image_path)。这不是 pipeline missing。",
            file=sys.stderr,
        )
        raise SystemExit(3)
    return run


def _plain_number(value):
    number = float(value)
    if number.is_integer():
        return int(number)
    return number


def _box_record(value) -> dict:
    x, y, w, h = parse_box(value)
    return {"x": _plain_number(x), "y": _plain_number(y), "w": _plain_number(w), "h": _plain_number(h)}


def _color_string(value):
    """颜色收成字符串。字典只取 color 键，不把缺字段写成 unknown。"""
    if isinstance(value, dict):
        return value.get("color")
    return value


def _stated_char_count(plate: dict):
    if "char_count" in plate and plate["char_count"] is not None:
        return int(plate["char_count"])
    segmentation = plate.get("segmentation")
    if isinstance(segmentation, dict) and segmentation.get("count") is not None:
        return int(segmentation["count"])
    return None


def normalize_plate(plate: dict) -> dict:
    """把提交仓库的一块牌收成指标用的字段。已有的旧字段保持优先。"""
    if not isinstance(plate, dict):
        raise ValueError("每块车牌必须是对象")
    out = dict(plate)
    if plate.get("box") is not None:
        out["box"] = _box_record(plate["box"])
    elif plate.get("bbox") is not None:
        out["box"] = _box_record(plate["bbox"])
    if "color" in plate:
        out["color"] = _color_string(plate["color"])
    count = _stated_char_count(plate)
    if count is not None:
        out["char_count"] = count
    if "number" not in plate and "text" in plate:
        out["number"] = plate.get("text")
    chars = plate.get("chars")
    if isinstance(chars, list) and any(not isinstance(item, str) for item in chars):
        out.pop("chars", None)
    return out


def coerce_prediction(result) -> dict:
    if isinstance(result, list):
        result = {"plates": result}
    if not isinstance(result, dict) or not isinstance(result.get("plates"), list):
        raise ValueError("pipeline.run 必须返回 {'plates': [...]}，或直接返回车牌列表")
    out = dict(result)
    out["plates"] = [normalize_plate(plate) for plate in result["plates"]]
    return out


def check_timer_helpers() -> None:
    if median([1, 2, 3, 4]) != 2.5 or median([1, 2, 3]) != 2:
        raise SystemExit("中位数计算与口径不一致")
    if percentile_nearest_rank([1, 2, 3, 4], 95) != 4:
        raise SystemExit("p95 最近秩与口径不一致")
    if abs(iou((0, 0, 100, 40), (0, 0, 50, 40)) - 0.5) > 1e-12:
        raise SystemExit("IoU 0.5 的手算对照失败")
    if abs(iou((10, 10, 100, 40), (10, 10, 100, 10)) - 0.25) > 1e-12:
        raise SystemExit("IoU 0.25 的手算对照失败")
    if canon_color("绿牌（新能源）") != "green":
        raise SystemExit("B 模块的绿色中文名没有映射到 green")
    system = coerce_prediction(
        {
            "plates": [
                {
                    "bbox": [10, 20, 30, 40],
                    "text": "京A12345",
                    "color": {"color": "blue", "label": "蓝牌"},
                    "segmentation": {"count": 7, "status": "ok"},
                    "chars": [[[0, 0]]],
                }
            ]
        }
    )["plates"][0]
    if system["box"] != {"x": 10, "y": 20, "w": 30, "h": 40}:
        raise SystemExit("bbox 列表没有收成 {x, y, w, h}")
    if system["color"] != "blue" or system["char_count"] != 7 or system["number"] != "京A12345":
        raise SystemExit("提交仓库的颜色、字数或号码没有收成指标字段")
    if "chars" in system:
        raise SystemExit("非字符串的 chars 仍被当成字符序列")
    aligned = coerce_prediction(
        {
            "plates": [
                {
                    "bbox": {"x": 1, "y": 2, "w": 3, "h": 4},
                    "text": "粤B88888",
                    "color": {"color": "yellow"},
                    "segmentation": {"count": 0},
                }
            ]
        }
    )["plates"][0]
    if aligned["box"] != {"x": 1, "y": 2, "w": 3, "h": 4} or aligned["char_count"] != 0:
        raise SystemExit("已经收成字典的 bbox，或字数为 0，没有按原值保留")
    old = coerce_prediction(
        {
            "plates": [
                {
                    "box": {"x": 0, "y": 0, "w": 8, "h": 4},
                    "bbox": [9, 9, 9, 9],
                    "number": "京A1",
                    "text": "沪B2",
                    "color": "blue",
                    "char_count": 4,
                    "segmentation": {"count": 8},
                    "chars": ["京", "A", "1"],
                }
            ]
        }
    )["plates"][0]
    if old["box"]["x"] != 0 or old["number"] != "京A1" or old["color"] != "blue":
        raise SystemExit("旧字段没有优先于提交仓库的字段")
    if old["char_count"] != 4 or old["chars"] != ["京", "A", "1"]:
        raise SystemExit("旧的字数或字符序列被改写了")
    if coerce_prediction({"plates": []})["plates"] != []:
        raise SystemExit("空 plates 没有保持为空")


def run_fixture(iou_threshold: float) -> int:
    check_timer_helpers()
    path = Path(__file__).resolve().parent / "fixtures" / "cases.json"
    fixture = load_json(path)
    threshold = float(fixture.get("iou_threshold", iou_threshold))
    if abs(iou_threshold - threshold) > 1e-12:
        print(
            f"夹具对照答案是按 IoU>={threshold} 计算的，本次仍使用该阈值。",
            file=sys.stderr,
        )
    images = []
    for case in fixture["cases"]:
        started = time.perf_counter()
        prediction = coerce_prediction(case["pred"])
        elapsed = time.perf_counter() - started
        images.append(
            {
                "image_id": case["image_id"],
                "gt": case["gt"],
                "pred": prediction,
                "elapsed_s": elapsed,
            }
        )
    report = public_report(score_images(images, threshold), threshold, "metric-self-check")
    expected = fixture["expected"]
    mismatches = []
    for field in COUNT_FIELDS:
        actual = _count_view(report, field)
        if actual != expected[field]:
            mismatches.append(f"{field}: 得到 {actual}，对照答案 {expected[field]}")
    if report["runtime"]["n_timed"] != report["n_images"]:
        mismatches.append("耗时张数和图像张数不一致")
    if report["is_system_measurement"]:
        mismatches.append("夹具被标成了系统实测")

    print("指标自检（合成夹具，不是系统实测，不能写入实验报告或测试表）")
    for line in summary_lines(report):
        print(line)
    if mismatches:
        print("夹具对照：不一致", file=sys.stderr)
        for item in mismatches:
            print(item, file=sys.stderr)
        return 1
    print("夹具对照：通过")
    return 0


def _count_view(report: dict, field: str) -> dict:
    if field == "localization":
        loc = report["localization"]
        return {"tp": loc["tp"], "fp": loc["fp"], "fn": loc["fn"]}
    if field == "character_on_hits":
        block = report["character"]["on_hits"]
    elif field == "character_end_to_end":
        block = report["character"]["end_to_end"]
    elif field == "full_plate_on_hits":
        block = report["full_plate"]["on_hits"]
    elif field == "full_plate_end_to_end":
        block = report["full_plate"]["end_to_end"]
    else:
        block = report[field]
    return {"correct": block["correct"], "total": block["total"]}


def _segmentation(plate: dict) -> dict:
    value = plate.get("segmentation")
    return value if isinstance(value, dict) else {}


def _recognition(plate: dict) -> dict:
    value = plate.get("recognition")
    return value if isinstance(value, dict) else {}


def _module_for_unmatched(pred: dict) -> tuple[str | None, str]:
    """只在流水线输出自己写明阶段时指出模块。"""
    error = pred.get("error") if isinstance(pred.get("error"), dict) else {}
    code = error.get("code")
    warnings = [str(item) for item in (pred.get("warnings") or [])]
    text = "；".join(warnings)
    if code == "detect_failed":
        return "检测", error.get("message") or code
    if "矫正失败" in text:
        return "矫正", text
    if "误检" in text or int(pred.get("rejected") or 0) > 0:
        return "集成过滤（D）", text or f"rejected={pred.get('rejected')}"
    if code == "no_plate":
        return "检测", error.get("message") or code
    return None, text


def _emitted_sources(pred_plates: list[dict], warnings: list) -> tuple[str | None, str]:
    sources = [str(plate.get("source")) for plate in pred_plates if plate.get("source")]
    parts = []
    if sources:
        parts.append("source=" + ",".join(sources))
    if warnings:
        parts.append("；".join(str(item) for item in warnings))
    if sources:
        return "检测", "；".join(parts)
    return None, "；".join(parts)


def _plate_module(pred_plate: dict, kind: str, count_matches: bool | None = None) -> tuple[str | None, str]:
    seg = _segmentation(pred_plate)
    rec = _recognition(pred_plate)
    source = pred_plate.get("source")
    if kind == "localization":
        if source:
            return "检测", f"source={source}"
        return None, ""
    if kind == "color":
        if "color" in pred_plate:
            return "颜色（B）", f"color={pred_plate.get('color')}"
        return None, "输出里没有 color"
    if kind == "char_count":
        if seg:
            detail = f"segmentation.count={seg.get('count')} status={seg.get('status')}"
            message = seg.get("message")
            if message:
                detail += f" message={message}"
            return "字符分割（B）", detail
        return None, "输出里没有 segmentation"
    if kind == "recognition":
        seg_note = f"segmentation.status={seg.get('status')} count={seg.get('count')}" if seg else ""
        rec_note = f"recognition.status={rec.get('status')} text={rec.get('text')}" if rec else ""
        if count_matches is False and seg:
            detail = seg_note
            if rec_note:
                detail += f"；{rec_note}"
            return "字符分割（B）", detail
        if rec:
            detail = rec_note
            if seg.get("status") not in (None, "", "ok") and seg_note:
                detail += f"；{seg_note}"
            return "字符识别（C）", detail
        if seg.get("status") not in (None, "", "ok"):
            return "字符分割（B）", seg_note
        if pred_plate.get("status"):
            return None, f"status={pred_plate.get('status')}"
        return None, ""
    return None, ""


def build_traces(images: list[dict], iou_threshold: float, manifest: dict) -> tuple[list[dict], list[dict]]:
    """逐图对照。号码为空的标注不进入逐字和整牌失败。不改计分。"""
    traces = []
    failures = []
    for image in images:
        image_id = image.get("image_id")
        split_name = _split_of(manifest, image_id)
        if image.get("error") or image.get("pred") is None:
            failure = {
                "image_id": image_id,
                "split": split_name,
                "item": "调用",
                "expected": "pipeline.run 返回 plates",
                "actual": image.get("error") or "missing prediction",
                "module": None,
                "evidence": "调用抛错，该图不进入准确率分母",
                "recognition_item": False,
            }
            failures.append(failure)
            traces.append(
                {
                    "image_id": image_id,
                    "split": split_name,
                    "error": failure["actual"],
                    "failures": [failure],
                }
            )
            continue
        gt = image["gt"]
        pred = image["pred"]
        gt_plates = list(gt.get("plates") or [])
        pred_plates = list(pred.get("plates") or [])
        matches, false_pos, false_neg = match_plates(gt_plates, pred_plates, iou_threshold)
        image_failures = []

        def add_failure(item, expected, actual, module, evidence, recognition_item):
            row = {
                "image_id": image_id,
                "split": split_name,
                "item": item,
                "expected": expected,
                "actual": actual,
                "module": module,
                "evidence": evidence,
                "recognition_item": recognition_item,
            }
            image_failures.append(row)
            failures.append(row)

        presence_ok = gt_present_local(gt) == (len(pred_plates) > 0)
        if not presence_ok:
            if (not gt.get("has_plate")) and pred_plates:
                module, evidence = _emitted_sources(pred_plates, pred.get("warnings") or [])
            else:
                module, evidence = _module_for_unmatched(pred)
            add_failure(
                "车牌是否存在",
                bool(gt.get("has_plate")),
                len(pred_plates) > 0,
                module,
                evidence,
                False,
            )
        matched_gt = {}
        for gi, pi, value in matches:
            matched_gt[gi] = (pi, value)
            gt_plate = gt_plates[gi]
            pred_plate = pred_plates[pi]
            scorable = has_scorable_text(gt_plate)
            gt_color = canon_color(gt_plate.get("color"))
            pred_color = canon_color(pred_plate.get("color"))
            if not (gt_color is not None and gt_color == pred_color):
                module, evidence = _plate_module(pred_plate, "color")
                add_failure("颜色", gt_plate.get("color"), pred_plate.get("color"), module, evidence, False)
            if gt_plate.get("char_count") is not None and stated_count(pred_plate) != int(gt_plate["char_count"]):
                module, evidence = _plate_module(pred_plate, "char_count")
                add_failure(
                    "字符数量",
                    int(gt_plate["char_count"]),
                    stated_count(pred_plate),
                    module,
                    evidence,
                    False,
                )
            if scorable:
                gt_seq = char_sequence(gt_plate)
                pred_seq = char_sequence(pred_plate)
                count_matches = None
                if gt_plate.get("char_count") is not None:
                    count_matches = stated_count(pred_plate) == int(gt_plate["char_count"])
                diffs = []
                for index, ch in enumerate(gt_seq):
                    got = pred_seq[index] if index < len(pred_seq) else ""
                    if got != ch:
                        diffs.append(f"{index}:{ch}->{got or '缺'}")
                if diffs:
                    module, evidence = _plate_module(pred_plate, "recognition", count_matches)
                    add_failure(
                        "逐字",
                        "".join(gt_seq),
                        "".join(pred_seq),
                        module,
                        evidence + (f"；错位 {', '.join(diffs)}" if evidence else f"错位 {', '.join(diffs)}"),
                        True,
                    )
                if plate_string(gt_plate) != plate_string(pred_plate):
                    module, evidence = _plate_module(pred_plate, "recognition", count_matches)
                    add_failure(
                        "整牌",
                        plate_string(gt_plate),
                        plate_string(pred_plate),
                        module,
                        evidence,
                        True,
                    )
        miss_module, miss_evidence = _module_for_unmatched(pred)
        for gi in false_neg:
            gt_plate = gt_plates[gi]
            scorable = has_scorable_text(gt_plate)
            add_failure(
                "定位",
                gt_plate.get("box"),
                "未配上",
                miss_module,
                miss_evidence,
                False,
            )
            if scorable:
                add_failure(
                    "整牌（端到端）",
                    plate_string(gt_plate),
                    "",
                    miss_module,
                    "没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。"
                    + (f" {miss_evidence}" if miss_evidence else ""),
                    True,
                )
        for pi in false_pos:
            pred_plate = pred_plates[pi]
            module, evidence = _plate_module(pred_plate, "localization")
            add_failure(
                "定位误检",
                "无对应标注框",
                pred_plate.get("box"),
                module,
                evidence,
                False,
            )
        plate_rows = []
        for gi, gt_plate in enumerate(gt_plates):
            matched = matched_gt.get(gi)
            pred_plate = pred_plates[matched[0]] if matched else None
            plate_rows.append(
                {
                    "plate_id": gt_plate.get("plate_id"),
                    "recognition_item": has_scorable_text(gt_plate),
                    "expected": {
                        "box": gt_plate.get("box"),
                        "number": plate_string(gt_plate),
                        "color": canon_color(gt_plate.get("color")),
                        "char_count": gt_plate.get("char_count"),
                    },
                    "actual": None
                    if pred_plate is None
                    else {
                        "box": pred_plate.get("box"),
                        "iou": matched[1],
                        "number": plate_string(pred_plate),
                        "color": canon_color(pred_plate.get("color")),
                        "char_count": stated_count(pred_plate),
                        "source": pred_plate.get("source"),
                        "status": pred_plate.get("status"),
                        "segmentation_status": _segmentation(pred_plate).get("status"),
                        "recognition_status": _recognition(pred_plate).get("status"),
                    },
                }
            )
        traces.append(
            {
                "image_id": image_id,
                "split": split_name,
                "relative_path": gt.get("relative_path"),
                "elapsed_s": image.get("elapsed_s"),
                "has_plate": bool(gt.get("has_plate")),
                "pred_count": len(pred_plates),
                "presence_correct": presence_ok,
                "tp": len(matches),
                "fp": len(false_pos),
                "fn": len(false_neg),
                "error_code": (pred.get("error") or {}).get("code") if isinstance(pred.get("error"), dict) else None,
                "warnings": pred.get("warnings") or [],
                "plates": plate_rows,
                "failures": image_failures,
            }
        )
    return traces, failures


def gt_present_local(gt: dict) -> bool:
    if "has_plate" in gt:
        return bool(gt["has_plate"])
    return len(gt.get("plates") or []) > 0


def _fmt_rate(block: dict) -> str:
    accuracy = block.get("accuracy")
    if accuracy is None:
        return f"{block['correct']}/{block['total']}"
    return f"{block['correct']}/{block['total']}（{accuracy:.6f}）"


def results_markdown(report: dict) -> str:
    loc = report["localization"]
    runtime = report["runtime"]
    lines = [
        "# 课程测试结果",
        "",
        "这次数字只来自 `eval/evaluate.py` 对冻结清单里 validation 和 final_test 的一次 `pipeline.run`。",
        "夹具分数和提交仓库的 8 张合成样本没有用在这里。号码归一化后为空的标注不参与逐字和整牌。",
        "",
        f"- 流水线：`{report.get('pipeline')}`",
        f"- 流水线提交：`{report.get('pipeline_commit')}`" if report.get("pipeline_commit") else "",
        report.get("pipeline_note") or "",
        f"- 划分：{', '.join(report.get('splits') or [])}",
        f"- IoU 阈值：{report['iou_threshold']}",
        f"- 图像 {report['n_images']}，调用错误 {report['n_errors']}",
        f"- 标注车牌 {report['n_gt_plates']}，预测车牌 {report['n_pred_plates']}",
        "",
        "## 指标",
        "",
        "| 指标 | 结果 |",
        "| --- | --- |",
        f"| 车牌是否存在 | {_fmt_rate(report['plate_presence'])} |",
        (
            f"| 定位精确率 | {loc['tp']}/{loc['tp'] + loc['fp']}"
            f"（{'' if loc['precision'] is None else f'{loc['precision']:.6f}'}） |"
        ),
        (
            f"| 定位召回率 | {loc['tp']}/{loc['tp'] + loc['fn']}"
            f"（{'' if loc['recall'] is None else f'{loc['recall']:.6f}'}） |"
        ),
        f"| 颜色 | {_fmt_rate(report['color'])} |",
        f"| 字符数量 | {_fmt_rate(report['char_count'])} |",
        f"| 逐字（定位命中后） | {_fmt_rate(report['character']['on_hits'])} |",
        f"| 逐字（端到端） | {_fmt_rate(report['character']['end_to_end'])} |",
        f"| 整牌（定位命中后） | {_fmt_rate(report['full_plate']['on_hits'])} |",
        f"| 整牌（端到端） | {_fmt_rate(report['full_plate']['end_to_end'])} |",
    ]
    if runtime["n_timed"]:
        lines.append(
            f"| 运行时间 | {runtime['n_timed']} 张，总和 {runtime['total_s']:.6f} 秒，"
            f"平均 {runtime['mean_s']:.6f} 秒，中位数 {runtime['median_s']:.6f} 秒，"
            f"p95 {runtime['p95_s']:.6f} 秒 |"
        )
    else:
        lines.append("| 运行时间 | 无 |")
    lines.extend(["", "## 逐图", "", "| 划分 | 图像 | 有牌 | 预测块数 | TP/FP/FN | 标注号码 | 预测号码 | 耗时（秒） |", "| --- | --- | --- | --- | --- | --- | --- | --- |"])
    for trace in report.get("traces") or []:
        if trace.get("error"):
            lines.append(
                f"| {trace.get('split')} | {trace['image_id']} |  |  |  |  | 调用错误 |  |"
            )
            continue
        expected_numbers = []
        actual_numbers = []
        for plate in trace["plates"]:
            number = plate["expected"]["number"] or "（空，不参与识别率）"
            expected_numbers.append(number)
            actual = plate["actual"]
            actual_numbers.append("未配上" if actual is None else (actual["number"] or "（空）"))
        elapsed = trace.get("elapsed_s")
        elapsed_text = "" if elapsed is None else f"{elapsed:.6f}"
        lines.append(
            "| {split} | {image} | {has} | {count} | {tp}/{fp}/{fn} | {expected} | {actual} | {elapsed} |".format(
                split=trace.get("split"),
                image=trace["image_id"],
                has="有" if trace["has_plate"] else "无",
                count=trace["pred_count"],
                tp=trace["tp"],
                fp=trace["fp"],
                fn=trace["fn"],
                expected="<br>".join(expected_numbers) or "无",
                actual="<br>".join(actual_numbers) or "无",
                elapsed=elapsed_text,
            )
        )
    lines.extend(["", "## 失败", "", "号码为空的牌不会出现在逐字或整牌行里。模块只在输出字段写明阶段时填写。", "", "| 图像 | 项目 | 期望 | 实际 | 模块 | 依据 |", "| --- | --- | --- | --- | --- | --- |"])
    failure_rows = report.get("failures") or []
    if not failure_rows:
        lines.append("|  |  |  |  |  | 本次没有失败项 |")
    for row in failure_rows:
        lines.append(
            "| {image} | {item} | {expected} | {actual} | {module} | {evidence} |".format(
                image=row["image_id"],
                item=row["item"],
                expected=_md(row["expected"]),
                actual=_md(row["actual"]),
                module=row["module"] or "",
                evidence=_md(row["evidence"]),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _md(value) -> str:
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def run_manifest(args) -> int:
    path = pipeline_path(args.pipeline)
    run = load_pipeline(path)
    manifest_path = Path(args.manifest) if args.manifest else ROOT / "data" / "splits" / "manifest.json"
    if not manifest_path.is_file():
        print(f"未找到清单：{manifest_path}", file=sys.stderr)
        return 4
    manifest = load_json(manifest_path)
    splits = [part.strip() for part in args.splits.split(",") if part.strip()]
    image_ids = selected_ids(manifest, splits)
    if not image_ids:
        print(
            f"划分 {', '.join(splits)} 里没有图像。没有调用流水线，也没有评测结果。"
        )
        return 0

    ann_path = Path(args.annotations) if args.annotations else ROOT / "data" / "annotations" / "annotations.jsonl"
    annotations = load_jsonl(ann_path)
    missing_ann = [image_id for image_id in image_ids if image_id not in annotations]
    if missing_ann:
        print("以下 image_id 在清单中，但标注里没有。已停止，没有输出指标：", file=sys.stderr)
        for image_id in missing_ann:
            print(image_id, file=sys.stderr)
        return 4

    data_tools = _load_data_tools()
    invalid = []
    missing_files = []
    resolved = []
    for image_id in image_ids:
        record = annotations[image_id]
        problems = data_tools.validate_annotation(record, allow_example=False)
        split_name = _split_of(manifest, image_id)
        if record.get("purpose") != split_name:
            problems.append(f"purpose 是 {record.get('purpose')}，清单划分是 {split_name}")
        if problems:
            invalid.append((image_id, problems))
            continue
        relative = record["relative_path"]
        image_path = (ROOT / relative).resolve()
        if not image_path.is_file():
            missing_files.append(f"{image_id} {relative}")
        else:
            resolved.append((record, image_path))
    if invalid or missing_files:
        print("标注或图像文件未就绪。已停止，没有输出指标。", file=sys.stderr)
        for image_id, problems in invalid:
            print(f"{image_id}: {'; '.join(problems)}", file=sys.stderr)
        for line in missing_files:
            print(f"缺少文件 {line}", file=sys.stderr)
        return 4

    images = []
    for record, image_path in resolved:
        started = time.perf_counter()
        try:
            prediction = coerce_prediction(run(str(image_path)))
            elapsed = time.perf_counter() - started
            images.append(
                {
                    "image_id": record["image_id"],
                    "gt": record,
                    "pred": prediction,
                    "elapsed_s": elapsed,
                }
            )
        except Exception as exc:
            images.append(
                {
                    "image_id": record["image_id"],
                    "gt": record,
                    "pred": None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    report = public_report(score_images(images, args.iou), args.iou, "system-evaluation")
    report["splits"] = splits
    report["pipeline"] = str(path)
    report["manifest"] = str(manifest_path)
    traces, failures = build_traces(images, args.iou, manifest)
    report["traces"] = traces
    report["failures"] = failures
    report["recognition_note"] = "号码归一化后为空的标注不参与逐字和整牌。夹具分数和 8 张合成样本不在本次结果里。"
    print("系统评测（由 pipeline.run 在清单图像上得到）")
    for line in summary_lines(report):
        print(line)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
        table_path = output.with_suffix(".md")
        table_path.write_text(results_markdown(report), encoding="utf-8")
        print(f"完整 JSON 已写入 {output}")
        print(f"逐图结果表已写入 {table_path}")
    else:
        print(text)
    return 0


def _split_of(manifest: dict, image_id: str) -> str | None:
    for name, ids in manifest.get("splits", {}).items():
        if image_id in ids:
            return name
    return None


def _load_data_tools():
    path = ROOT / "data" / "check_dataset.py"
    spec = importlib.util.spec_from_file_location("check_dataset", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按清单评测车牌流水线，或运行指标夹具。")
    parser.add_argument("--fixture", action="store_true", help="运行合成夹具，不调用 pipeline.py")
    parser.add_argument("--manifest", default=None, help="划分清单 JSON，默认 data/splits/manifest.json")
    parser.add_argument("--annotations", default=None, help="标注 JSONL，默认 data/annotations/annotations.jsonl")
    parser.add_argument("--pipeline", default=None, help="pipeline.py 路径，默认仓库根目录")
    parser.add_argument(
        "--splits",
        default="validation,final_test",
        help="逗号分隔的划分，默认 validation,final_test",
    )
    parser.add_argument("--iou", type=float, default=DEFAULT_IOU_THRESHOLD, help="定位命中的 IoU 阈值")
    parser.add_argument("--output", default=None, help="把系统评测 JSON 写到这个文件")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.fixture:
        return run_fixture(args.iou)
    return run_manifest(args)


if __name__ == "__main__":
    raise SystemExit(main())
