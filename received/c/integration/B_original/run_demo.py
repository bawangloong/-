# -*- coding: utf-8 -*-
"""
run_demo.py —— B 模块演示与过程图生成

对 samples/ 下每张车牌：
    1) 识别颜色（plate_color）
    2) 分割字符（segment_chars）
    3) 输出四联过程图：原始车牌 / 二值化 / 字符框 / 逐个字符切片
    4) 打印并保存结果汇总（output/summary.csv）

用法：
    python run_demo.py                # 处理 samples/ 全部
    python run_demo.py 某张牌.png      # 处理指定图片
"""

import csv
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from plate_color import classify_plate_color, is_dark_text_on_light_plate
from segment_chars import segment_plate, CHAR_H, CHAR_W

SRC_DIR = "samples"
OUT_DIR = "output"
PANEL_W = 900


def _font(size=18):
    for p in ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _to_pil(a):
    a = np.asarray(a)
    if a.dtype != np.uint8:
        a = a.astype(np.uint8)
    if a.ndim == 2:
        return Image.fromarray(a, mode="L").convert("RGB")
    return Image.fromarray(a, mode="RGB")


def make_panel(plate_rgb, res, color_info, path):
    """拼四联图：原图 / 二值化 / 字符框 / 字符切片"""
    st = res["stages"]
    norm, bw, boxes = st["norm"], st["bw"], res["boxes"]

    im_plate = _to_pil(norm)
    im_bw = Image.fromarray((bw * 255).astype(np.uint8), mode="L").convert("RGB")

    # 字符框
    im_box = im_plate.copy()
    d = ImageDraw.Draw(im_box)
    for i, (x, y, w, h) in enumerate(boxes):
        d.rectangle([x, y, x + w, y + h], outline=(255, 60, 60), width=2)
        d.text((x, max(0, y - 16)), str(i + 1), fill=(255, 60, 60), font=_font(14))

    # 字符切片条
    slot = 60
    strip = Image.new("RGB", (max(1, len(res["chars"])) * slot, CHAR_H + 8), (250, 250, 250))
    for i, ch in enumerate(res["chars"]):
        tile = Image.fromarray(ch, mode="L").convert("RGB")
        strip.paste(tile, (i * slot + (slot - CHAR_W) // 2, 4))

    W = max(im_plate.width, im_bw.width, im_box.width, strip.width, 420)
    rows = [(im_plate, "1 原始车牌（归一化）"),
            (im_bw, "2 二值化"),
            (im_box, "3 字符定位框"),
            (strip, "4 字符切片")]
    PAD, LH = 30, 24
    H = sum(im.height + LH + 10 for im, _ in rows) + 80
    canvas = Image.new("RGB", (W + PAD * 2, H), (255, 255, 255))
    d = ImageDraw.Draw(canvas)
    d.text((PAD, 10), "%s  |  颜色：%s（置信度 %.2f）  |  字符数：%d  |  状态：%s"
           % (os.path.basename(path), color_info["label"], color_info["confidence"],
              res["count"], res["status"]), fill=(20, 20, 20), font=_font(18))
    y = 44
    for im, title in rows:
        d.text((PAD, y), title, fill=(90, 90, 90), font=_font(15))
        y += LH
        canvas.paste(im, (PAD, y))
        y += im.height + 10
    return canvas


def process(path):
    img = np.array(Image.open(path).convert("RGB"))
    color_info = classify_plate_color(img)
    res = segment_plate(
        img,
        prefer_dark_text=is_dark_text_on_light_plate(color_info["color"]),
        debug=True,
    )
    return img, color_info, res


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [os.path.join(SRC_DIR, f) for f in sorted(os.listdir(SRC_DIR))
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]

    rows = []
    for p in files:
        img, cinfo, res = process(p)
        panel = make_panel(img, res, cinfo, p)
        out = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(p))[0] + "_panel.png")
        panel.save(out)

        # 逐个字符单独保存，便于 C 同学直接拿来建库/测试
        cdir = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(p))[0] + "_chars")
        os.makedirs(cdir, exist_ok=True)
        for i, ch in enumerate(res["chars"]):
            Image.fromarray(ch, mode="L").save(os.path.join(cdir, "char_%02d.png" % (i + 1)))

        rows.append([os.path.basename(p), cinfo["label"], cinfo["confidence"],
                     res["count"], res["status"], out])
        print("%-18s 颜色=%-8s 置信度=%.2f 字符数=%d 状态=%s -> %s"
              % (os.path.basename(p), cinfo["label"], cinfo["confidence"],
                 res["count"], res["status"], out))

    with open(os.path.join(OUT_DIR, "summary.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["图片", "颜色", "置信度", "字符数", "状态", "过程图"])
        w.writerows(rows)
    print("\n汇总已写入", os.path.join(OUT_DIR, "summary.csv"))


if __name__ == "__main__":
    main()
