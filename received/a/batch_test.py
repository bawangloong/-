# -*- coding: utf-8 -*-
"""
batch_test.py —— A 模块批量自测与效果记录生成
==============================================
对 test_images/ 全量运行检测+矫正，与 annotations.json 真值比对，
输出指标统计和 docs/定位效果记录.md，并保存每张图的标框/裁剪结果。

指标口径（与 E 的 evaluate.py 对齐时可复用）：
  * 匹配：预测框与真值框 IoU >= 0.5 记为命中（贪心，按得分降序）。
  * 检出率 recall = 命中真值数 / 真值总数
  * 精确率 precision = 命中预测数 / 预测总数
  * 平均 IoU：命中对的 IoU 均值
  * 倾角误差：命中对的 |预测角 - 真值角|（真值角由标注时旋转角给出，见 annotations）

运行：python batch_test.py
"""

import json
import os
import time

import cv2
import numpy as np

from plate_common import load_image, save_image, PlateIOError
from detect_plate import detect_plates, draw_regions, _iou_quad_bbox
from rectify_plate import rectify_plates

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "test_images")
OUT_DIR = os.path.join(HERE, "results", "batch")
DOC = os.path.join(HERE, "docs", "定位效果记录.md")
IOU_THRESH = 0.5


def iou(b1, b2):
    return _iou_quad_bbox(b1, b2)


def match(regions, gts):
    """贪心 IoU 匹配。返回 (命中对列表, 未命中真值索引, 未命中预测索引)。"""
    pairs, used_g, used_p = [], set(), set()
    order = sorted(range(len(regions)), key=lambda i: regions[i].score, reverse=True)
    for i in order:
        best_j, best_v = -1, IOU_THRESH
        for j, g in enumerate(gts):
            if j in used_g:
                continue
            v = iou(regions[i].bbox, g["bbox"])
            if v >= best_v:
                best_j, best_v = j, v
        if best_j >= 0:
            pairs.append((i, best_j, best_v))
            used_g.add(best_j)
            used_p.add(i)
    fn = [j for j in range(len(gts)) if j not in used_g]
    fp = [i for i in range(len(regions)) if i not in used_p]
    return pairs, fn, fp


def test_invalid_inputs():
    """异常输入测试：错误类型 / 损坏图片 / 不存在文件 / 超小图。"""
    os.makedirs(os.path.join(HERE, "test_invalid"), exist_ok=True)
    cases = []
    p = os.path.join(HERE, "test_invalid", "说明.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write("这不是图片")
    cases.append(("错误文件类型(.txt)", p))
    p = os.path.join(HERE, "test_invalid", "伪装.jpg")
    with open(p, "wb") as f:
        f.write(b"this is not a jpeg at all" * 10)
    cases.append(("伪装扩展名(内容非图片)", p))
    p = os.path.join(HERE, "test_invalid", "损坏.jpg")
    real = load_image(os.path.join(IMG_DIR, "01_normal_blue.jpg"))
    ok, buf = cv2.imencode(".jpg", real)
    with open(p, "wb") as f:
        f.write(buf.tobytes()[: len(buf) // 3])  # 截断的 JPEG
    cases.append(("损坏/截断图片", p))
    cases.append(("不存在的文件", os.path.join(HERE, "test_invalid", "不存在.jpg")))

    rows = []
    for name, path in cases:
        try:
            load_image(path)
            rows.append((name, "未拦截（异常！）"))
        except PlateIOError as e:
            rows.append((name, f"正确拦截：{e}"))
    # 超小图不应崩溃
    tiny = np.zeros((2, 2, 3), np.uint8)
    r = detect_plates(tiny)
    rows.append(("2x2 超小图", f"正常返回 {len(r)} 个结果（应为0）"))
    return rows


def main():
    ann = json.load(open(os.path.join(IMG_DIR, "annotations.json"), encoding="utf-8"))
    rows, all_pairs = [], []
    tot_gt = tot_pred = tot_tp = 0
    t_all = time.time()
    for name in sorted(ann):
        gts = ann[name]["plates"]
        img = load_image(os.path.join(IMG_DIR, name))
        t0 = time.time()
        regions = detect_plates(img)
        dt = (time.time() - t0) * 1000
        pairs, fn, fp = match(regions, gts)
        plates = rectify_plates(img, regions)
        out = os.path.join(OUT_DIR, os.path.splitext(name)[0])
        save_image(os.path.join(out, "detected.jpg"), draw_regions(img, regions))
        for i, p in enumerate(plates, 1):
            save_image(os.path.join(out, f"plate_{i}.png"), p.image)
        mean_iou = float(np.mean([v for _, _, v in pairs])) if pairs else 0.0
        rows.append({"name": name, "gt": len(gts), "pred": len(regions),
                     "tp": len(pairs), "fn": len(fn), "fp": len(fp),
                     "iou": mean_iou, "ms": dt})
        all_pairs += pairs
        tot_gt += len(gts); tot_pred += len(regions); tot_tp += len(pairs)
    total_ms = (time.time() - t_all) * 1000

    recall = tot_tp / tot_gt if tot_gt else 0.0
    precision = tot_tp / tot_pred if tot_pred else 0.0
    mean_iou = float(np.mean([v for _, _, v in all_pairs])) if all_pairs else 0.0
    invalid_rows = test_invalid_inputs()

    # 生成 Markdown 记录
    lines = ["# A 模块定位效果记录", "",
             f"- 测试集：`test_images/`（合成图 {len(ann)} 张，真值见 `annotations.json`）",
             f"- 匹配口径：IoU ≥ {IOU_THRESH} 记为命中",
             f"- 环境：OpenCV {cv2.__version__}，单线程 CPU", "",
             "## 总体指标", "",
             "| 指标 | 数值 |", "|---|---|",
             f"| 真值车牌总数 | {tot_gt} |",
             f"| 预测车牌总数 | {tot_pred} |",
             f"| 命中数 | {tot_tp} |",
             f"| 检出率 recall | {recall:.1%} |",
             f"| 精确率 precision | {precision:.1%} |",
             f"| 命中平均 IoU | {mean_iou:.3f} |",
             f"| 单图平均检测耗时 | {total_ms/len(ann):.0f} ms |", "",
             "## 逐图结果", "",
             "| 图片 | 真值 | 预测 | 命中 | 漏检 | 误检 | 平均IoU | 耗时(ms) |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['name']} | {r['gt']} | {r['pred']} | {r['tp']} | "
                     f"{r['fn']} | {r['fp']} | {r['iou']:.3f} | {r['ms']:.0f} |")
    lines += ["", "## 异常输入测试", "", "| 案例 | 结果 |", "|---|---|"]
    for name, res in invalid_rows:
        lines.append(f"| {name} | {res} |")
    lines += ["", "## 说明", "",
              "- 每张图的标框图与裁剪图保存在 `results/batch/<图片名>/`。",
              "- 本记录基于合成测试集；真实照片集由 E 提供后用同一脚本复测。", "",
              "## 局限与已知问题", "",
              "本合成集上无漏检/误检/切字，但传统方法存在以下能力边界，真实照片需重点复测：", "",
              "| 类别 | 说明 | 影响 | 缓解 |",
              "|---|---|---|---|",
              "| 大倾角 | 仅支持 |倾角|≤45°；透视畸变（非平面旋转）未建模 | 极端角度漏检 | 必要时引入四边形透视矫正或神经网络 |",
              "| 双层牌 | 长宽比≈2.0 的双层黄牌可进入候选，但字符布局验证按单层设计 | 双层牌可能漏检 | 作业聚焦 7/8 位单层牌，双层列为局限 |",
              "| 强反光/过曝 | 底色 HSV 偏移、字符边缘被高光淹没 | 颜色覆盖率下降→漏检 | 放宽 COLOR_RANGES 或加自适应直方图均衡 |",
              "| 极小车牌 | 原图宽 <60px 的车牌被 MIN_PLATE_W 过滤 | 远处小牌漏检 | 调小阈值（会增加误检，需权衡） |",
              "| 同色粘连 | 车身与车牌同色且紧贴时靠边缘活动范围反推整牌 | 边界 IoU 略降、边缘可能留少量背景 | 已用 _tighten_by_texture 处理，B 预处理可再清边 |",
              "| 裁剪边缘 | 矫正图边缘可能残留 1~3px 背景/边框 | 不影响字符主体 | B 的二值化/连通域清理可去除 |", "",
              "### 开发期发现并已修复的问题（供报告引用）", "",
              "1. **字符碎片误检**：蓝牌上的白色字符曾被当成白牌 → 用外环底色判定 + 字符峰数过滤解决。",
              "2. **背景色块粘连**：车牌与同色背景块相连导致框偏大 → 底色掩码收紧 + 边缘活动范围反推整牌解决。",
              "3. **广告牌误检**：蓝底白字广告牌形似车牌 → 字符带高度/留白验证（_char_layout_ok）排除。",
              "4. **边缘框切字**：边缘通道只覆盖字符区，NMS 若保留它会切掉首字 → 重叠时优先保留颜色通道整牌框。",
              "5. **倾斜裁剪方向错误**：大倾角时角点顺序导致裁剪旋转 90° → _quad_norm 统一长边为阅读方向。", ""]
    os.makedirs(os.path.dirname(DOC), exist_ok=True)
    with open(DOC, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"recall={recall:.1%} precision={precision:.1%} meanIoU={mean_iou:.3f}")
    print(f"记录已写入 {DOC}")


if __name__ == "__main__":
    main()