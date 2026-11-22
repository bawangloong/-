# -*- coding: utf-8 -*-
"""
run_demo.py —— A 模块独立运行示例（检测 + 矫正一条龙）
======================================================
用法：
    python run_demo.py 图片路径 [--out 输出目录]

输出（默认 results/<图片名>/）：
    detected.png   原图标框图（绿框 + 序号 + 底色线索 + 得分）
    plate_1.png …  每块车牌的矫正裁剪图（交给 B 的就是这些图）
    result.json    定位结果 + 矫正尺寸 + 坐标映射矩阵

异常输入（错误类型/损坏图片/不存在）会给出中文提示并以退出码 2 结束，
D 的 GUI 直接捕获 PlateIOError 即可。
"""

import argparse
import os
import sys

from plate_common import load_image, save_image, regions_to_json, PlateIOError
from detect_plate import detect_plates, draw_regions
from rectify_plate import rectify_plates


def run(image_path: str, out_dir: str | None = None) -> int:
    try:
        img = load_image(image_path)
    except PlateIOError as e:
        print(f"[输入错误] {e}")
        return 2

    name = os.path.splitext(os.path.basename(image_path))[0]
    out = out_dir or os.path.join("results", name)

    regions = detect_plates(img)
    save_image(os.path.join(out, "detected.png"), draw_regions(img, regions))

    if not regions:
        print("未检测到车牌（无车牌或全部候选被过滤）。")
        with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
            f.write(regions_to_json([], {"image": image_path}))
        return 0

    plates = rectify_plates(img, regions)
    extra = {"image": image_path, "rectified": []}
    for i, p in enumerate(plates, 1):
        path = os.path.join(out, f"plate_{i}.png")
        save_image(path, p.image)
        extra["rectified"].append({
            "index": i,
            "file": f"plate_{i}.png",
            "size_wh": list(p.size),
            "transform": p.transform.tolist(),
        })
        print(f"车牌 #{i}: 位置={p.region.bbox} 倾角={p.region.angle:.1f}° "
              f"底色线索={p.region.color_hint} 得分={p.region.score:.2f} "
              f"矫正图={p.size[0]}x{p.size[1]} → {path}")

    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "result.json"), "w", encoding="utf-8") as f:
        f.write(regions_to_json(regions, extra))
    print(f"共 {len(regions)} 块车牌。标框图与 JSON 已保存到 {out}/")
    return 0


def main():
    ap = argparse.ArgumentParser(description="A 模块独立示例：检测+矫正")
    ap.add_argument("image", help="输入图片路径（支持中文路径）")
    ap.add_argument("--out", default=None, help="输出目录，默认 results/<图片名>/")
    args = ap.parse_args()
    sys.exit(run(args.image, args.out))


if __name__ == "__main__":
    main()