"""将输入、归一化结果和 Top3 不同类别样本绘成黑字说明图。"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from char_features import normalize_character, to_gray


def font(size):
    for name in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
                 "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                 "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def tile(image, size=76):
    image = Image.fromarray(np.asarray(image, dtype=np.uint8))
    image.thumbnail((size, size), Image.Resampling.NEAREST)
    result = Image.new("RGB", (size, size), "white")
    result.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    return result


def save_match_sheet(images, results, recognizer, output, title="字符样本库匹配过程"):
    """纯色/坏图也可出图；每行保留对应的输入位置。"""
    width, row_height, top = 1120, 145, 105
    canvas = Image.new("RGB", (width, top + max(len(images), 1) * row_height + 35), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((25, 16), title, font=font(26), fill="black")
    columns = [25, 200, 390, 630, 870]
    for x, heading in zip(columns, ["输入字符", "归一化", "候选 1", "候选 2", "候选 3"]):
        draw.text((x, 67), heading, font=font(19), fill="black")
    for index, source in enumerate(images):
        y = top + index * row_height
        result = results[index] if index < len(results) else {"candidates": [], "label": "?"}
        try:
            raw = to_gray(source)
            canvas.paste(tile(raw), (columns[0], y))
            normalized = normalize_character(source)
            canvas.paste(tile(255 - normalized), (columns[1], y))
        except (ValueError, OSError):
            draw.rectangle((columns[0], y, columns[0] + 76, y + 76), outline="black")
            draw.text((columns[1], y + 20), "无效输入", font=font(18), fill="black")
        draw.text((columns[0], y + 83), f"位置 {index + 1}", font=font(16), fill="black")
        for column, candidate in enumerate(result.get("candidates", [])[:3]):
            x = columns[column + 2]
            sample = recognizer.normalized_images[candidate["sample_index"]]
            canvas.paste(tile(255 - sample), (x, y))
            draw.text((x + 85, y + 12), candidate["label"], font=font(28), fill="black")
            draw.text((x, y + 83), f"相似度 {candidate['similarity']:.4f}", font=font(16), fill="black")
        status = result.get("status", "")
        state = {"ok": "正常", "needs_review": "建议复核", "invalid_input": "无效"}.get(status, status)
        draw.text((columns[1], y + 106), f"输出 {result['label']} / {state}", font=font(15), fill="black")
        draw.line((25, y + row_height - 10, width - 25, y + row_height - 10), fill="black")
    draw.text((25, canvas.height - 27), "分数为余弦相似度，不是正确概率。候选对应不同类别。", font=font(16), fill="black")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def save_library_sheet(recognizer, output):
    labels = list(recognizer.class_indices)
    columns, cell_width, cell_height = 13, 90, 118
    rows = (len(labels) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_width + 30, rows * cell_height + 90), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 12), "65 类字符库示例（每类首个训练样本）", font=font(25), fill="black")
    for index, label in enumerate(labels):
        x, y = 15 + index % columns * cell_width, 63 + index // columns * cell_height
        sample_index = recognizer.class_indices[label][0]
        canvas.paste(tile(255 - recognizer.normalized_images[sample_index], 65), (x, y))
        draw.text((x, y + 69), f"{label} ({len(recognizer.class_indices[label])})", font=font(17), fill="black")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)


def save_failure_sheet(paths, truth, predictions, output):
    count = min(16, len(paths))
    canvas = Image.new("RGB", (1120, 85 + ((count + 7) // 8) * 145), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 15), "独立测试集错误样本（按文件顺序取前 16 个）", font=font(25), fill="black")
    for i in range(count):
        x, y = 20 + i % 8 * 138, 75 + i // 8 * 145
        canvas.paste(tile(255 - normalize_character(paths[i]), 80), (x, y))
        draw.text((x, y + 85), f"真值 {truth[i]}", font=font(18), fill="black")
        draw.text((x, y + 111), f"预测 {predictions[i]}", font=font(18), fill="black")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
