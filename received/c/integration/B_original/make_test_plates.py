# -*- coding: utf-8 -*-
"""
make_test_plates.py —— 生成合成车牌，用于自测（不是真实数据）

用途：A 同学的真实车牌到位前，先用合成图把颜色识别与字符分割跑通。
生成：samples/ 下若干张蓝、黄、绿、白、黑车牌，含 7 位与 8 位、轻微倾斜。
"""

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = "samples"
FONT_PATHS = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
              "C:/Windows/Fonts/simsun.ttc"]

SPECS = [
    # (文件名, 底色, 字色, 号码, 尺寸, 倾斜角)
    ("blue_7.png",   (10, 70, 200),   (255, 255, 255), "京A·12345", (440, 140), 0),
    ("yellow_7.png", (240, 200, 30),  (20, 20, 20),    "沪B·88888", (440, 140), 0),
    ("green_8.png",  (120, 220, 140), (20, 20, 20),    "粤C·D12345", (480, 140), 0),
    ("white_7.png",  (245, 245, 245), (20, 20, 20),    "苏E·66T78", (440, 140), 0),
    ("black_7.png",  (25, 25, 28),    (250, 250, 250), "浙F·A1B2C", (440, 140), 0),
    ("blue_tilt.png", (10, 70, 200),  (255, 255, 255), "冀D·97531", (440, 140), 6),
]


def _font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_plate(bg, fg, text, size, angle=0):
    w, h = size
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    # 外框
    d.rectangle([1, 1, w - 2, h - 2], outline=fg, width=2)
    # 字符
    f = _font(int(h * 0.55))
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]), text, font=f, fill=fg)
    # 铆钉
    for x in (int(w * 0.06), int(w * 0.94)):
        for y in (int(h * 0.12), int(h * 0.88)):
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=fg)
    if angle:
        img = img.rotate(angle, expand=True, fillcolor=bg,
                         resample=Image.BICUBIC)
    return img


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, bg, fg, text, size, ang in SPECS:
        im = make_plate(bg, fg, text, size, ang)
        path = os.path.join(OUT_DIR, name)
        im.save(path)
        print("生成", path, im.size)


if __name__ == "__main__":
    main()
