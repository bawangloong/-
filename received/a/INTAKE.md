# 角色 E 收下的 A 模块

来源是发布页 https://github.com/bawangloong/plate-recognition-submit/releases/tag/v1.0 的资源 `A_plate_detection_1.zip`（页面标签 `A_plate_detection(1).zip`）。SHA-256：`214171e7846b3dda9bb493e326185dc1fe703a9b8777298bb2ca445d39b1e69d`。压缩包顶层目录 `A_plate_detection/` 已展开到这里，代码没有改。

在 `received/a/` 里运行。依赖是 OpenCV 和 NumPy，Python 3.10 及以上。`requirements.txt` 写的是 `opencv-python==4.11.0.86`。

```bash
python run_demo.py test_images/01_normal_blue.jpg
python detect_plate.py 图片路径 --out results
python rectify_plate.py 图片路径 --out results
```

`run_demo.py` 会在 `results/<图名>/` 写下标框图、每块摆正的 `plate_*.png` 和 `result.json`。

## 实际接口

内存里的图是 OpenCV 的 BGR `uint8`，形状 `(H, W, 3)`。读图用 `plate_common.load_image(path)`，支持中文路径。文件不存在、类型不对或图片损坏时抛 `PlateIOError`。支持的扩展名在 `SUPPORTED_EXTS`。

```python
from plate_common import load_image
from detect_plate import detect_plates
from rectify_plate import rectify_plates

image = load_image("某图.jpg")
regions = detect_plates(image)          # list[PlateRegion]，按 score 从高到低；没有车牌就是 []
plates = rectify_plates(image, regions) # list[RectifiedPlate]，与 regions 一一对应
```

`PlateRegion`：`bbox` 是原图上的 `(x, y, w, h)` 整数；`quad` 是四个角点，顺序为左上、右上、右下、左下；`angle` 是倾角；`score` 是 0 到 1；`color_hint` 只是 `blue` / `yellow` / `green` / `white` / `unknown`，最终颜色仍由 B 判定。

`RectifiedPlate`：`image` 是摆正后的 BGR 车牌图，交给 B 之前要转成 RGB，因为 B 的 `classify_plate_color` 默认按 RGB 读；`region` 指回检测框；`transform` 是 3×3 矩阵，原图齐次坐标映射到矫正图。`bbox` 可以直接拿来算定位 IoU。

## 和课程测试表的关系

包里有合成图 `test_images/`、真实照片 `test_real_images/`，以及 `docs/` 里 A 自己写的效果记录。E 没有复跑这些脚本，也没有把那些数字写进课程测试表。这些图没有进入 `data/splits/manifest.json`。
