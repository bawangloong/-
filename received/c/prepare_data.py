"""下载固定版本公开样本，按归一化图像去重后分层划分数据。

首次原始数据准备需要联网及支持 7z 的 tar。交付包已附分好的图片，
日常构库、识别和评估均可离线运行，无需再执行本程序。
"""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.error
import urllib.request

import numpy as np

from char_features import normalize_character, read_image
from labels import ALL_LABELS, FOLDER_TO_LABEL, LABEL_TO_FOLDER

ROOT = Path(__file__).resolve().parent
REPO = "wzh191920/License-Plate-Recognition"
COMMIT = "34ba808ea2563b3b2ff7266b9cc6d0d9a98f52b1"
SOURCES = {
    "chars2.7z": (3336217, "6687c3379a464bb0a63fd00deedcf1252daca8b5"),
    "charsChinese.7z": (1099009, "5e4a173a20a1f3421f18f333b9857332d287ed40"),
}


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "plate-character-coursework"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == 3:
                raise
            print(f"下载连接失败，第 {attempt + 1}/4 次：{exc}；稍后重试", flush=True)
            time.sleep(2 * (attempt + 1))


def prepare(cache, output, seed):
    if (output / "data_manifest.csv").exists():
        raise ValueError("目标已有数据清单，请指定一个新的 --output，避免覆盖已有划分")
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    notices = output / "third_party"
    notices.mkdir(exist_ok=True)
    base_url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/"
    for source, target in [("LICENSE", "sample_source_MIT_LICENSE.txt"),
                           ("README.md", "sample_source_README.md")]:
        (notices / target).write_bytes(download(base_url + source))
    (notices / "EasyPR_APACHE_LICENSE.txt").write_bytes(download(
        "https://raw.githubusercontent.com/liuruoze/EasyPR/c32d69c50439f02b3ab9b4230048b2895d876d16/LICENSE"))
    tar = shutil.which("tar")
    if tar is None and Path("C:/Windows/System32/tar.exe").is_file():
        tar = "C:/Windows/System32/tar.exe"
    if tar is None:
        raise RuntimeError("原始数据解压需要可读取 7z 的 tar；随包数据不需要再次解压")
    sources = []
    extracted = cache / "extracted"
    extracted.mkdir(exist_ok=True)
    for filename, (expected_size, expected_blob) in SOURCES.items():
        archive = cache / filename
        if not archive.is_file():
            archive.write_bytes(download(base_url + "train/" + filename))
        content = archive.read_bytes()
        api_url = f"https://api.github.com/repos/{REPO}/contents/train/{filename}?ref={COMMIT}"
        official = json.loads(download(api_url))
        blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if len(content) != expected_size or blob != expected_blob or blob != official["sha"]:
            raise ValueError(f"数据校验失败 {filename}")
        listing = subprocess.check_output([tar, "-tf", str(archive)], text=True, encoding="utf-8")
        for name in listing.splitlines():
            target = (extracted / name).resolve()
            if not target.is_relative_to(extracted.resolve()):
                raise ValueError("压缩包包含越界路径")
        subprocess.run([tar, "-xf", str(archive), "-C", str(extracted)], check=True)
        sources.append({"file": filename, "url": base_url + "train/" + filename,
                        "bytes": len(content), "git_blob_sha1": blob,
                        "sha256": hashlib.sha256(content).hexdigest()})

    records = []
    invalid = []
    for path in sorted(extracted.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".png", ".bmp"}:
            continue
        label = FOLDER_TO_LABEL.get(path.parent.name)
        if label is None:
            invalid.append({"source": str(path.relative_to(extracted)), "reason": "unsupported_folder"})
            continue
        try:
            image = read_image(path)
            normalized = normalize_character(image)
        except ValueError as exc:
            invalid.append({"source": str(path.relative_to(extracted)), "reason": str(exc)})
            continue
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        pixel_hash = hashlib.sha256(normalized.tobytes()).hexdigest()
        records.append({"label": label, "path": path, "source": path.relative_to(extracted).as_posix(),
                        "sha256": raw_hash, "normalized_sha256": pixel_hash})

    groups = defaultdict(list)
    for record in records:
        groups[record["normalized_sha256"]].append(record)
    kept = defaultdict(list)
    excluded = []
    for group in groups.values():
        if len({record["label"] for record in group}) > 1:
            for record in group:
                excluded.append({**record, "reason": "conflicting_labels"})
        else:
            kept[group[0]["label"]].append(group[0])
            for record in group[1:]:
                excluded.append({**record, "reason": "duplicate_normalized_pixels"})
    rng = np.random.default_rng(seed)
    manifest = []
    per_class = {}
    for label in ALL_LABELS:
        examples = sorted(kept[label], key=lambda record: record["source"])
        if len(examples) < 5:
            raise ValueError(f"{label} 独立样本不足 5 张")
        order = rng.permutation(len(examples))
        n_test = max(1, round(len(examples) * 0.15))
        n_val = max(1, round(len(examples) * 0.15))
        split_counts = Counter()
        for index, selected in enumerate(order):
            split = "test" if index < n_test else "validation" if index < n_test + n_val else "train"
            record = examples[int(selected)]
            folder = LABEL_TO_FOLDER[label]
            relative = Path("character_library" if split == "train" else "evaluation_data") / split / folder
            relative = relative / (record["sha256"][:20] + record["path"].suffix.lower())
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record["path"], destination)
            manifest.append({k: v for k, v in record.items() if k != "path"} |
                            {"split": split, "file": relative.as_posix()})
            split_counts[split] += 1
        per_class[label] = dict(split_counts)
    with (output / "data_manifest.csv").open("w", encoding="utf-8-sig", newline="") as file:
        fields = ["file", "split", "label", "source", "sha256", "normalized_sha256"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)
    for record in excluded:
        record.pop("path", None)
    summary = {
        "seed": seed, "repository": "https://github.com/" + REPO, "commit": COMMIT,
        "sources": sources, "raw_supported_images": len(records), "kept_images": len(manifest),
        "split_counts": dict(Counter(record["split"] for record in manifest)),
        "classes": len(per_class), "per_class": per_class,
        "excluded_counts": dict(Counter(record["reason"] for record in excluded)),
        "invalid_count": len(invalid), "deduplication": "32x32 normalized grayscale SHA256, before splitting",
        "mapping_correction": "upstream zh_qing uses 靑; this module emits 青",
        "limitation": "within-source stratified split; near-duplicates and common original plates cannot be ruled out",
    }
    (output / "data_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (notices / "excluded_samples.json").write_text(json.dumps(excluded + invalid, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT)
    parser.add_argument("--seed", type=int, default=20261116)
    args = parser.parse_args()
    prepare(args.cache.resolve(), args.output.resolve(), args.seed)
