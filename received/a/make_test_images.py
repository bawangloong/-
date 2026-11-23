# -*- coding: utf-8 -*-
"""
make_test_images.py —— 生成 A 模块合成测试集（带真值标注）
==========================================================
用途：在没有真实数据集时验证检测/矫正逻辑，并作为回归测试基线。
真实照片测试集由 E 提供，接口相同（见 README）。

运行：python make_test_images.py
输出：test_images/*.jpg + test_images/annotations.json
      annotations.json 格式: {文件名: {"plates": [{"bbox":[x,y,w,h], "text":..., "color":...}]}}
      （无车牌图片 plates 为空列表）
"""

import json
import math
import os
import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

random.seed(42)
np.random.seed(42)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
LATIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PLATE_COLORS = {
    "blue":   ((20, 60, 160), (255, 255, 255)),
    "yellow": ((235, 190, 30), (20, 20, 20)),
    "green":  ((120, 200, 120), (20, 20, 20)),
    "white":  ((240, 240, 240), (20, 20, 20)),
}


def make_plate(text: str, color: str, width: int = 440) -> Image.Image:
    """画一块仿真车牌。text 如 '京A12345'（7位）或 '粤BD12345'（8位）。
    字符逐个渲染后压缩到单元格内（真实车牌字符为窄长形），避免重叠。"""
    bg, fg = PLATE_COLORS[color]
    w = width
    h = int(round(w * 140 / (480 if len(text) >= 8 else 440)))
    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)
    bw = max(2, w // 90)
    d.rectangle([bw, bw, w - bw - 1, h - bw - 1], outline=fg, width=bw)
    n = len(text)
    usable = w - 2 * bw - 8
    cell = usable / (n + 0.5)          # 0.5 为间隔圆点留位
    char_w = int(cell * 0.78)
    char_h = int(h * 0.66)
    fsize = int(h * 0.9)
    f_cjk = ImageFont.truetype(CJK, fsize)
    f_lat = ImageFont.truetype(LATIN, fsize)
    x = bw + 4
    for i, ch in enumerate(text):
        f = f_cjk if ord(ch) > 0x2E80 else f_lat
        fill = (200, 30, 30) if (color == "white" and i == n - 1) else fg
        # 先在大画布上渲染单字，裁出墨迹范围，再缩放到窄长单元格
        tmp = Image.new("L", (fsize * 2, fsize * 2), 0)
        ImageDraw.Draw(tmp).text((fsize // 2, fsize // 2), ch, font=f, fill=255)
        bb = tmp.getbbox()
        glyph = tmp.crop(bb).resize((char_w, char_h), Image.LANCZOS)
        colored = Image.new("RGB", glyph.size, fill)
        img.paste(colored, (int(x + (cell - char_w) / 2), int(h * 0.17)), glyph)
        x += cell
        if i == 1:  # 第2位后的间隔圆点
            r = max(2, w // 110)
            cx, cy = x + cell * 0.25, h / 2
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)
            x += cell * 0.5
    return img


def make_scene(w: int, h: int) -> Image.Image:
    """合成街景背景：渐变 + 随机色块 + 噪声（模拟车身/路面/建筑）。"""
    top = np.array([random.randint(120, 200)] * 3, float)
    bot = np.array([random.randint(40, 90)] * 3, float)
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (top * (1 - t) + bot * t) * np.ones((1, w, 1))
    arr += np.random.normal(0, 8, (h, w, 3))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(random.randint(4, 8)):
        x0, y0 = random.randint(0, w - 80), random.randint(0, h - 60)
        x1, y1 = x0 + random.randint(60, 220), y0 + random.randint(40, 160)
        c = tuple(random.randint(30, 180) for _ in range(3))
        d.rectangle([x0, y0, min(x1, w), min(y1, h)], fill=c)
    return img


def paste_plate(scene: Image.Image, plate: Image.Image, cx: int, cy: int,
                angle: float = 0.0):
    """把车牌贴到场景 (cx,cy) 中心，旋转 angle 度。返回轴对齐真值 bbox。"""
    rot = plate.rotate(angle, expand=True, resample=Image.BICUBIC,
                       fillcolor=None)
    # 用 alpha 通道避免旋转补角干扰背景
    rgba = plate.convert("RGBA").rotate(angle, expand=True, resample=Image.BICUBIC)
    px, py = int(cx - rgba.width / 2), int(cy - rgba.height / 2)
    scene.paste(rgba, (px, py), rgba)
    # 真值：旋转后四角（去掉 expand 的透明边，用原始牌尺寸算）
    w, h = plate.size
    a = math.radians(-angle)  # PIL 逆时针为正，图像坐标 y 向下
    corners = []
    for dx, dy in [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]:
        rx = dx * math.cos(a) - dy * math.sin(a)
        ry = dx * math.sin(a) + dy * math.cos(a)
        corners.append((cx + rx, cy + ry))
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    bbox = [int(min(xs)), int(min(ys)),
            int(max(xs) - min(xs)), int(max(ys) - min(ys))]
    return bbox


def build():
    os.makedirs(OUT, exist_ok=True)
    ann = {}

    def save(name, scene, plates):
        scene.save(os.path.join(OUT, name), quality=92)
        ann[name] = {"plates": plates}

    # 1 正常蓝牌
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("京A12345", "blue"), 500, 420)
    save("01_normal_blue.jpg", s, [{"bbox": b, "text": "京A12345", "color": "blue"}])

    # 2 倾斜蓝牌 +12°
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("沪B67890", "blue"), 500, 400, angle=12)
    save("02_tilt_pos12.jpg", s, [{"bbox": b, "text": "沪B67890", "color": "blue"}])

    # 3 倾斜蓝牌 -9°
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("浙C24680", "blue"), 520, 380, angle=-9)
    save("03_tilt_neg9.jpg", s, [{"bbox": b, "text": "浙C24680", "color": "blue"}])

    # 4 黄牌
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("苏D13579", "yellow"), 480, 430)
    save("04_yellow.jpg", s, [{"bbox": b, "text": "苏D13579", "color": "yellow"}])

    # 5 新能源绿牌 8 位
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("粤BD12345", "green", width=480), 500, 420)
    save("05_green_8char.jpg", s, [{"bbox": b, "text": "粤BD12345", "color": "green"}])

    # 6 白色警牌
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("京A1234警", "white"), 500, 420)
    save("06_white_police.jpg", s, [{"bbox": b, "text": "京A1234警", "color": "white"}])

    # 7 多车牌（3 块，其中一块倾斜）
    s = make_scene(1400, 900)
    p1 = paste_plate(s, make_plate("京A11111", "blue", 360), 350, 500, angle=0)
    p2 = paste_plate(s, make_plate("沪C22222", "yellow", 340), 900, 350, angle=8)
    p3 = paste_plate(s, make_plate("粤BF33333", "green", 380), 1050, 700, angle=-6)
    save("07_multi_3plates.jpg", s, [
        {"bbox": p1, "text": "京A11111", "color": "blue"},
        {"bbox": p2, "text": "沪C22222", "color": "yellow"},
        {"bbox": p3, "text": "粤BF33333", "color": "green"}])

    # 8 小车牌（大图中的远处车牌）
    s = make_scene(1600, 1000)
    b = paste_plate(s, make_plate("川A55555", "blue", width=110), 1200, 600)
    save("08_small_plate.jpg", s, [{"bbox": b, "text": "川A55555", "color": "blue"}])

    # 9 模糊
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("鲁B66666", "blue"), 500, 420)
    arr = cv2.GaussianBlur(np.array(s), (7, 7), 2)
    save("09_blur.jpg", Image.fromarray(arr),
         [{"bbox": b, "text": "鲁B66666", "color": "blue"}])

    # 10 低光照
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("闽C77777", "blue"), 500, 420)
    arr = (np.array(s).astype(float) * 0.45).astype(np.uint8)
    save("10_dark.jpg", Image.fromarray(arr),
         [{"bbox": b, "text": "闽C77777", "color": "blue"}])

    # 11 干扰物：蓝底广告牌（长宽比不符）+ 真车牌
    s = make_scene(1200, 800)
    d = ImageDraw.Draw(s)
    d.rectangle([80, 60, 620, 300], fill=(25, 70, 170))  # 蓝色大广告牌
    f = ImageFont.truetype(CJK, 90)
    d.text((120, 110), "欢迎光临", font=f, fill=(255, 255, 255))
    b = paste_plate(s, make_plate("冀D88888", "blue"), 700, 550)
    save("11_distractor.jpg", s, [{"bbox": b, "text": "冀D88888", "color": "blue"}])

    # 12 无车牌
    s = make_scene(1000, 700)
    save("12_no_plate.jpg", s, [])

    # 13 无车牌但有文字广告牌
    s = make_scene(1000, 700)
    d = ImageDraw.Draw(s)
    d.rectangle([150, 150, 850, 330], fill=(200, 200, 205))
    f = ImageFont.truetype(CJK, 100)
    d.text((190, 180), "停车场入口", font=f, fill=(30, 30, 30))
    save("13_no_plate_text.jpg", s, [])

    # 14 极端倾斜 30°（能力边界案例）
    s = make_scene(1000, 700)
    b = paste_plate(s, make_plate("豫E99999", "blue"), 500, 400, angle=30)
    save("14_tilt30.jpg", s, [{"bbox": b, "text": "豫E99999", "color": "blue"}])

    with open(os.path.join(OUT, "annotations.json"), "w", encoding="utf-8") as fp:
        json.dump(ann, fp, ensure_ascii=False, indent=2)
    print(f"已生成 {len(ann)} 张测试图 → {OUT}")


if __name__ == "__main__":
    build()