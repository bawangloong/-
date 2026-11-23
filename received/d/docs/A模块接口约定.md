# A 模块接口约定（D 集成用）

D 的统一入口只依赖两个函数。A 的代码放在 `vendor/a_plate/` 下，D 启动时会自动
检测；文件存在就接管，不存在就用内置兜底（`app/detector.py`）。

## 1. 目录

```
vendor/a_plate/
├── detect_plate.py
└── rectify_plate.py
```

## 2. `detect_plate.py`

```python
def detect_plates(image_bgr: numpy.ndarray) -> list[dict]:
    """
    参数：image_bgr —— OpenCV BGR 图像，shape=(h, w, 3)，dtype=uint8。
    返回：列表，每块车牌一个 dict；没有车牌返回 []。
    """
```

每个元素：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `bbox` | `(x, y, w, h)` | 是 | 原图坐标，整数，左上角 + 宽高 |
| `quad` | 4×2 数组 | 否 | 原图坐标的四角点，顺序不限（D 会重排） |
| `score` | float | 否 | 检测置信度 0~1，用于排序 |

约束：

- 坐标必须对应**原图**，不要返回缩放后图像的坐标；
- 一张图可返回多块车牌，D 会逐块处理并把结果列在界面左侧；
- 同一块车牌不要重复返回（重复框会显示成多块）；
- 函数不应修改传入的 `image_bgr`。

## 3. `rectify_plate.py`

```python
def rectify_plate(image_bgr: numpy.ndarray, plate: dict) -> numpy.ndarray | None:
    """
    参数：原图 + detect_plates 返回的同一个 dict。
    返回：方向正常、字符完整的车牌 BGR 图像；失败返回 None。
    """
```

可选：如果只提供 `detect_plate.py`，D 会按 `plate["quad"]` 自己做透视矫正；
但为了倾斜车牌的效果，建议 A 提供自己的矫正实现。

## 4. 最小示例

```python
# vendor/a_plate/detect_plate.py
import cv2
import numpy as np

def detect_plates(image_bgr):
    results = []
    # ... A 的检测算法 ...
    # results.append({"bbox": (x, y, w, h), "quad": quad, "score": 0.9})
    return results

# vendor/a_plate/rectify_plate.py
import cv2
import numpy as np

def rectify_plate(image_bgr, plate):
    if plate.get("quad") is None:
        x, y, w, h = plate["bbox"]
        return image_bgr[y:y + h, x:x + w].copy()
    src = np.float32(plate["quad"])
    dst = np.float32([[0, 0], [439, 0], [439, 139], [0, 139]])
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(image_bgr, matrix, (440, 140))
```

## 5. 替换后的检查清单

1. 把两个 `.py` 放进 `vendor/a_plate/`；
2. 运行 `python tools/smoke_test.py`，确认 8 张演示图结果；
3. 打开 GUI 选图，检查多车牌是否都列出、框是否贴合；
4. 用 `tests/test_pipeline.py` 回归，确认没有破坏 B/C 接口；
5. 打包时确认 `vendor/a_plate/` 被放进发行目录（`build/make_portable.ps1`
   或 PyInstaller spec 已包含 `vendor` 整个目录）。

## 6. 与 D 的分工边界

- A 只负责“整图 → 车牌框/矫正图”；颜色、分割、识别由 B/C 完成；
- A 返回空列表时，D 统一提示“未检测到车牌”，不视为程序错误；
- A 内部异常会被 D 捕获并显示为“车牌检测失败”，同时写入日志。
