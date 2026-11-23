"""离线交付验收：校验载荷、行为测试、重建库与评估/联调结果一致性。"""

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

import numpy as np

from build_library import build_library
from evaluate_chars import evaluate
from integration_example import run_demo

ROOT = Path(__file__).resolve().parent


def verify(output):
    record = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "working_copy": str(ROOT), "python": platform.python_version(), "checks": {}}
    manifest = ROOT / "checksums.sha256"
    files = 0
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError("哈希清单含越界路径")
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError(f"文件哈希不一致：{name}")
        files += 1
    record["payload_manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    record["checks"]["payload_hashes"] = {"passed": True, "files": files,
                                             "note": "manifest excludes itself, acceptance_record.json and Python caches"}
    process = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    log = process.stdout + process.stderr
    if process.returncode != 0:
        raise RuntimeError(log)
    record["checks"]["behavior_tests"] = {"passed": True, "log": log}
    with tempfile.TemporaryDirectory(prefix="plate_C_acceptance_") as directory:
        temporary = Path(directory)
        with contextlib.redirect_stdout(io.StringIO()):
            build_library(ROOT / "character_library/train", temporary / "rebuilt.npz")
        with np.load(temporary / "rebuilt.npz", allow_pickle=False) as rebuilt, np.load(ROOT / "character_library/library.npz", allow_pickle=False) as delivered:
            if set(rebuilt.files) != set(delivered.files):
                raise ValueError("重新构库字段不一致")
            for key in delivered.files:
                if not np.array_equal(rebuilt[key], delivered[key]):
                    raise ValueError(f"重新构库数组不一致：{key}")
        record["checks"]["rebuilt_library_arrays"] = {"passed": True, "comparison": "every saved array exactly equal, including metadata"}
        with contextlib.redirect_stdout(io.StringIO()):
            metrics = evaluate("test", temporary / "test", temporary / "rebuilt.npz")
        reference = json.loads((ROOT / "results/test/metrics.json").read_text(encoding="utf-8"))
        for key in ["count", "classes", "feature_version", "unrestricted", "type_constrained", "review_thresholds", "common_confusions"]:
            if metrics[key] != reference[key]:
                raise ValueError(f"重跑评估结果不一致：{key}")
        record["checks"]["test_metrics_reproduced"] = {"passed": True, "count": metrics["count"],
                                                        "top1_accuracy": metrics["unrestricted"]["all"]["top1_accuracy"],
                                                        "note": "timing and machine-dependent environment excluded"}
        with contextlib.redirect_stdout(io.StringIO()):
            integration = run_demo(output=temporary / "B")
        reference = json.loads((ROOT / "results/B_integration/summary.json").read_text(encoding="utf-8"))
        if integration != reference:
            raise ValueError("重跑 B 联调汇总不一致")
        for name in ["blue_7", "green_8", "black_7", "yellow_7", "white_7", "blue_tilt"]:
            actual = json.loads((temporary / "B" / (name + ".json")).read_text(encoding="utf-8"))
            expected = json.loads((ROOT / "results/B_integration" / (name + ".json")).read_text(encoding="utf-8"))
            if actual != expected:
                raise ValueError(f"B 完整 JSON 不一致：{name}")
        record["checks"]["b_integration_reproduced"] = {"passed": True, "images": integration["images"],
                                                         "exact_matches": integration["exact_matches"],
                                                         "abnormal_segmentation": integration["abnormal_segmentation"]}
        cli = []
        for name, expected_text in [("blue_7", "京A12345"), ("green_8", "粤CD12345")]:
            target = temporary / (name + ".json")
            process = subprocess.run([sys.executable, str(ROOT / "recognize_chars.py"), "--chars-dir",
                                      str(ROOT / "integration/B_original/output" / (name + "_chars")), "--output", str(target)],
                                     capture_output=True)
            result = json.loads(target.read_text(encoding="utf-8"))
            if process.returncode != 0 or result["text"] != expected_text:
                raise ValueError(f"CLI 示例复现失败：{name}")
            cli.append({"sample": name, "text": result["text"], "exit_code": process.returncode})
        record["checks"]["cli_7_and_8"] = {"passed": True, "results": cli}
    record["all_checks_passed"] = all(check["passed"] for check in record["checks"].values())
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"all_checks_passed": record["all_checks_passed"], "output": str(output),
                      "payload_files": files}, ensure_ascii=False, indent=2))
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "acceptance_record.json")
    args = parser.parse_args()
    verify(args.output)
