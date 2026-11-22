"""接口、失败行为、独立距离核验、真实数据隔离以及 B 模块回归。"""

import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_library import build_library
from char_features import FEATURE_DIM, HOG_DIM, character_feature, normalize_character, read_image, write_image
from integration_example import BToC, recognize_b_result
from labels import ALL_LABELS, LABEL_TO_FOLDER
from recognize_chars import CharacterRecognizer, natural_key


class CharacterModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recognizer = CharacterRecognizer()
        cls.paths = {label: ROOT / "character_library/train" / cls.recognizer.sample_paths[indices[0]]
                     for label, indices in cls.recognizer.class_indices.items()}
        cls.image = read_image(cls.paths["A"])

    def test_library_coverage_dimensions_and_unit_vectors(self):
        self.assertEqual(set(self.recognizer.class_indices), set(ALL_LABELS))
        self.assertEqual(HOG_DIM, 324)
        self.assertEqual(FEATURE_DIM, 1348)
        np.testing.assert_allclose(np.linalg.norm(self.recognizer.features, axis=1), 1, atol=1e-6)

    def test_unicode_image_path(self):
        with tempfile.TemporaryDirectory(prefix="车牌C_") as directory:
            path = Path(directory) / "汉字目录" / "京字符.png"
            write_image(path, self.image)
            np.testing.assert_array_equal(read_image(path), self.image)

    def test_inverse_polarity(self):
        np.testing.assert_array_equal(normalize_character(self.image), normalize_character(255 - self.image))

    def test_supported_array_formats(self):
        binary = normalize_character(self.image) > 127
        expected = normalize_character(binary)
        for image in [binary.astype(np.float32), binary.astype(np.uint8), binary.astype(np.uint8) * 255,
                      np.repeat((binary * 255).astype(np.uint8)[:, :, None], 3, axis=2)]:
            np.testing.assert_array_equal(normalize_character(image), expected)
        bgr = np.repeat((binary * 255).astype(np.uint8)[:, :, None], 3, axis=2)
        bgra = np.dstack((bgr, np.full(binary.shape, 255, dtype=np.uint8)))
        np.testing.assert_array_equal(normalize_character(bgra), expected)

    def test_reject_invalid_inputs_without_crashing(self):
        bad = [None, np.empty((0, 0), np.uint8), np.zeros((40, 20), np.uint8),
               np.full((40, 20), np.nan), np.full((40, 20), 2.0),
               np.ones((40, 20), np.uint16), np.zeros((40, 20, 2), np.uint8)]
        for image in bad:
            with self.subTest(shape=getattr(image, "shape", None)):
                result = self.recognizer.recognize_char(image)
                self.assertEqual(result["status"], "invalid_input")
                self.assertEqual(result["label"], "?")

    def test_exact_sample_and_distinct_top3(self):
        result = self.recognizer.recognize_char(self.paths["京"])
        self.assertEqual(result["label"], "京")
        self.assertAlmostEqual(result["similarity"], 1, places=5)
        self.assertEqual(len({c["label"] for c in result["candidates"]}), 3)
        result = self.recognizer.recognize_char(self.paths["京"], top_k=1)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertIsNotNone(result["margin"])

    def test_rank_matches_independent_float64_euclidean_distances(self):
        _, query = character_feature(self.paths["5"])
        # 单位向量上最大内积等价于最小平方欧氏距离，独立核验候选类别和分数。
        distances = np.sum((self.recognizer.features.astype(np.float64) - query.astype(np.float64)) ** 2, axis=1)
        class_distances = {label: float(np.min(distances[indices])) for label, indices in self.recognizer.class_indices.items()}
        expected = sorted(class_distances, key=lambda label: (class_distances[label], ALL_LABELS.index(label)))[:3]
        result = self.recognizer.rank_features(query[None])[0]
        self.assertEqual([c["label"] for c in result["candidates"]], expected)
        for candidate in result["candidates"]:
            self.assertAlmostEqual(candidate["similarity"], 1 - class_distances[candidate["label"]] / 2, places=5)

    def test_seven_and_eight_character_api(self):
        for text in ["京A12345", "粤CD12345"]:
            result = self.recognizer.recognize_chars([self.paths[label] for label in text])
            self.assertEqual(result["text"], text)
            self.assertEqual(result["character_count"], len(text))
            self.assertEqual([r["position"] for r in result["characters"]], list(range(len(text))))

    def test_bad_char_preserves_position(self):
        images = [self.paths[label] for label in "京A12345"]
        images[3] = np.zeros((40, 20), dtype=np.uint8)
        result = self.recognizer.recognize_chars(images)
        self.assertEqual(result["text"], "京A1?345")
        self.assertEqual(result["status"], "partial_failure")

    def test_no_chars_invalid_length_and_unrestricted(self):
        self.assertEqual(self.recognizer.recognize_chars([])["status"], "no_characters")
        images = [self.paths[label] for label in "A1234"]
        self.assertEqual(self.recognizer.recognize_chars(images)["status"], "invalid_length")
        self.assertEqual(self.recognizer.recognize_chars(images, layout="unrestricted")["text"], "A1234")

    def test_review_and_argument_errors(self):
        recognizer = CharacterRecognizer(review_margin=1)
        self.assertEqual(recognizer.recognize_char(self.paths["A"])["status"], "needs_review")
        with self.assertRaises(ValueError):
            recognizer.recognize_char(self.paths["A"], top_k=0)
        with self.assertRaises(ValueError):
            recognizer.recognize_char(self.paths["A"], allowed_labels=["警"])
        with self.assertRaises(ValueError):
            recognizer.recognize_chars([self.image], layout="typo")

    def test_immutable_inputs_and_repeatable_results(self):
        before = self.image.copy()
        first = self.recognizer.recognize_char(self.image)
        second = self.recognizer.recognize_char(self.image)
        self.assertEqual(first, second)
        np.testing.assert_array_equal(self.image, before)
        self.assertFalse(self.recognizer.features.flags.writeable)

    def test_natural_filename_order(self):
        paths = list(map(Path, ["char_10.png", "char_2.png", "char_01.png"]))
        self.assertEqual([p.name for p in sorted(paths, key=natural_key)], ["char_01.png", "char_2.png", "char_10.png"])

    def test_all_delivered_data_hashes_and_split_isolation(self):
        with (ROOT / "data_manifest.csv").open(encoding="utf-8-sig", newline="") as file:
            records = list(csv.DictReader(file))
        with (ROOT / "font_samples_manifest.csv").open(encoding="utf-8-sig", newline="") as file:
            font_records = list(csv.DictReader(file))
        seen = {}
        for record in records + font_records:
            path = ROOT / record["file"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])
            digest = hashlib.sha256(normalize_character(path).tobytes()).hexdigest()
            self.assertEqual(digest, record["normalized_sha256"])
            self.assertNotIn(digest, seen, f"重复图像跨划分或跨字体模板：{path}")
            seen[digest] = record["split"]
        self.assertEqual(len(self.recognizer.labels), sum(r["split"] == "train" for r in records) + len(font_records))

    def test_rebuild_deduplication_and_conflict_detection(self):
        with tempfile.TemporaryDirectory(prefix="字符库测试_") as directory:
            samples = Path(directory) / "train"
            write_image(samples / "A" / "one.png", self.image)
            write_image(samples / "A" / "duplicate.png", self.image)
            output = Path(directory) / "library.npz"
            with contextlib.redirect_stdout(io.StringIO()):
                metadata = build_library(samples, output)
            self.assertEqual(metadata["samples"], 1)
            self.assertEqual(len(metadata["excluded_duplicate_samples"]), 1)
            self.assertEqual(CharacterRecognizer(output).recognize_char(self.image)["label"], "A")
            write_image(samples / "B" / "wrong_label.png", self.image)
            with self.assertRaisesRegex(ValueError, "不同字符"):
                build_library(samples, output)

    def test_b_delivery_pixel_reproduction_and_abnormal_count(self):
        bridge = BToC()
        b_dir = ROOT / "integration/B_original"
        for path in sorted((b_dir / "samples").glob("*.png")):
            result, segmentation = bridge.run(np.asarray(Image.open(path).convert("RGB")))
            archived = sorted((b_dir / "output" / (path.stem + "_chars")).glob("*.png"), key=natural_key)
            self.assertEqual(len(archived), len(segmentation["chars"]))
            for saved, actual in zip(archived, segmentation["chars"]):
                np.testing.assert_array_equal(read_image(saved), actual)
            if path.stem == "blue_tilt":
                self.assertEqual(result["recognition"]["status"], "invalid_length")
                self.assertEqual(result["recognition"]["text"], "")
        with self.assertRaisesRegex(ValueError, "不一致"):
            recognize_b_result({"chars": [self.image], "count": 7, "status": "ok"}, self.recognizer)

    def test_cli_failure_exit_and_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            process = subprocess.run([sys.executable, str(ROOT / "recognize_chars.py"), "--chars-dir",
                                      str(ROOT / "integration/B_original/output/blue_tilt_chars"), "--output", str(output)],
                                     capture_output=True, text=True, encoding="utf-8", errors="replace")
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "invalid_length")


if __name__ == "__main__":
    unittest.main(verbosity=2)
