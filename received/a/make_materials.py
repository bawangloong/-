# -*- coding: utf-8 -*-
"""
make_materials.py —— 生成 A 模块讲解素材（流程图 + 结果对照图）
运行：python make_materials.py   （需先运行 batch_test.py 生成 results/batch/）
输出：docs/流程图.png、docs/结果对照.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
DOCS = os.path.join(HERE, "docs")


def font(sz):
    return ImageFont.truetype(CJK, sz)


def flow_diagram():
    W, H = 1400, 760
    img = Image.new("RGB", (W, H), (250, 250, 252))
    d = ImageDraw.Draw(img)
    d.text((40, 24), "A 模块：车牌检测 · 定位 · 矫正 流程", font=font(34), fill=(20, 20, 20))
    steps = [
        ("① 输入原图", "BGR·中文路径", (70, 110, 180)),
        ("② 预处理", "缩放·HSV·Sobel", (95, 130, 75)),
        ("③ 双通道候选", "颜色掩码+边缘", (190, 140, 50)),
        ("④ 几何筛选", "长宽比·尺寸·倾角", (160, 95, 125)),
        ("⑤ 收紧验证", "底色·字符峰·布局", (130, 85, 165)),
        ("⑥ 评分去重", "综合得分·NMS", (70, 140, 140)),
        ("⑦ 透视矫正", "摆正·微调·去框", (190, 105, 75)),
        ("⑧ 输出结果", "车牌图+坐标映射", (55, 135, 95)),
    ]
    bw, bh = 280, 96
    gap_x, gap_y = 60, 70
    per_row = 4
    x0 = (W - (per_row * bw + (per_row - 1) * gap_x)) // 2
    y0 = 110
    centers = []
    for i, (title, sub, color) in enumerate(steps):
        r, c = divmod(i, per_row)
        x = x0 + c * (bw + gap_x)
        y = y0 + r * (bh + gap_y)
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=14, fill=color)
        d.text((x + 20, y + 16), title, font=font(26), fill=(255, 255, 255))
        d.text((x + 20, y + 56), sub, font=font(20), fill=(255, 255, 255))
        centers.append((x, y, x + bw, y + bh))
    # 同行箭头
    for r in range(2):
        for c in range(per_row - 1):
            i = r * per_row + c
            x1, y1, x2, y2 = centers[i]
            nx1, ny1, _, _ = centers[i + 1]
            ay = y1 + bh // 2
            d.line([x2 + 4, ay, nx1 - 8, ay], fill=(70, 70, 70), width=3)
            d.polygon([(nx1 - 8, ay - 7), (nx1 - 8, ay + 7), (nx1, ay)], fill=(70, 70, 70))
    # 换行箭头：第④(行0末)→第⑤(行1首)
    x1, y1, x2, y2 = centers[3]
    nx1, ny1, nx2, ny2 = centers[4]
    midy = (y2 + ny1) // 2
    d.line([x2 + 4, y1 + bh // 2, x2 + 30, y1 + bh // 2], fill=(70, 70, 70), width=3)
    d.line([x2 + 30, y1 + bh // 2, x2 + 30, midy], fill=(70, 70, 70), width=3)
    d.line([x2 + 30, midy, nx1 - 30, midy], fill=(70, 70, 70), width=3)
    d.line([nx1 - 30, midy, nx1 - 30, ny1 + bh // 2], fill=(70, 70, 70), width=3)
    d.line([nx1 - 30, ny1 + bh // 2, nx1 - 8, ny1 + bh // 2], fill=(70, 70, 70), width=3)
    d.polygon([(nx1 - 8, ny1 + bh // 2 - 7), (nx1 - 8, ny1 + bh // 2 + 7),
               (nx1, ny1 + bh // 2)], fill=(70, 70, 70))
    # 输出契约说明
    ty = y0 + 2 * (bh + gap_y) + 10
    d.text((x0, ty), "输出契约（plate_common.py，全组统一）", font=font(26), fill=(20, 20, 20))
    notes = [
        "PlateRegion：bbox(x,y,w,h) + quad(四角点) + angle + score + color_hint，坐标均对应原图",
        "RectifiedPlate：摆正车牌图(BGR) + transform(3×3 单应矩阵，原图→矫正图)",
        "无车牌返回空列表 []；异常输入抛 PlateIOError（供 GUI 提示）",
        "交接：裁剪图→B 分割｜detect_plates 接口→D 集成｜定位结果→E 评估",
    ]
    yy = ty + 44
    for t in notes:
        d.text((x0 + 10, yy), "• " + t, font=font(21), fill=(45, 45, 45))
        yy += 38
    img.save(os.path.join(DOCS, "流程图.png"))
    print("已生成 docs/流程图.png")


def contact_sheet():
    cases = [
        ("01_normal_blue", "正常蓝牌"),
        ("02_tilt_pos12", "倾斜 +12°"),
        ("05_green_8char", "新能源绿牌(8位)"),
        ("06_white_police", "白色警牌"),
        ("07_multi_3plates", "多车牌(3块)"),
        ("14_tilt30", "大倾角 30°"),
    ]
    cell_w, cell_h = 460, 230
    pad, label_h = 16, 34
    cols = 2
    rows = (len(cases) + cols - 1) // cols
    W = cols * cell_w + (cols + 1) * pad
    H = rows * (cell_h + label_h) + (rows + 1) * pad + 60
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((pad, 14), "A 模块检测矫正结果对照（左：原图标框 / 右：矫正裁剪）",
           font=font(26), fill=(20, 20, 20))
    for idx, (key, label) in enumerate(cases):
        r, c = divmod(idx, cols)
        x = pad + c * (cell_w + pad)
        y = 60 + pad + r * (cell_h + label_h + pad)
        d.text((x, y), f"{label}", font=font(20), fill=(30, 30, 30))
        base = os.path.join(HERE, "results", "batch", key)
        det = Image.open(os.path.join(base, "detected.jpg")).convert("RGB")
        det.thumbnail((cell_w // 2 - 6, cell_h - 8))
        dx, dy = x, y + label_h + (cell_h - 8 - det.height) // 2
        img.paste(det, (dx, dy))
        d.rectangle([dx - 1, dy - 1, dx + det.width, dy + det.height], outline=(180, 180, 180))
        # 拼接该案例所有车牌裁剪（横向，统一高度、垂直居中）
        crops = []
        i = 1
        while os.path.exists(os.path.join(base, f"plate_{i}.png")):
            crops.append(Image.open(os.path.join(base, f"plate_{i}.png")).convert("RGB"))
            i += 1
        if crops:
            ch = 70  # 统一裁剪展示高度
            resized = [cr.resize((int(cr.width * ch / cr.height), ch)) for cr in crops]
            total_w = sum(r.width for r in resized) + 6 * (len(resized) - 1)
            avail = cell_w // 2 - 6
            scale = min(1.0, avail / total_w)
            xx = x + cell_w // 2 + 4
            cy = y + label_h + (cell_h - 8) // 2
            for r in resized:
                rr = r.resize((max(1, int(r.width * scale)), max(1, int(r.height * scale))))
                ry = cy - rr.height // 2
                img.paste(rr, (xx, ry))
                d.rectangle([xx - 1, ry - 1, xx + rr.width, ry + rr.height],
                            outline=(180, 180, 180))
                xx += rr.width + 6
    img.save(os.path.join(DOCS, "结果对照.png"))
    print("已生成 docs/结果对照.png")


if __name__ == "__main__":
    os.makedirs(DOCS, exist_ok=True)
    flow_diagram()
    contact_sheet()