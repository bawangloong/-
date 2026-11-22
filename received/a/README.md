# A 模块：车牌检测 · 定位 · 矫正

> 视频多媒体实践课大作业 —— 车牌识别系统
> 本目录是 **A 同学** 的交付模块，负责把整张图片中的车牌找出来、摆正、裁剪好，交给后续同学。
> **B/C/D/E 请先读「§3 接口契约」和各自对应的交接章节，再开始你们的模块。**

## 0. 这个模块做什么（一句话）

输入一张原始图片 → 输出图中**每一块**车牌的「位置 + 摆正后的裁剪图」。

- **检测**：判断有没有车牌、有几块，给出每块在原图中的坐标。
- **定位**：用四边形（quad）精确框出车牌，支持倾斜车牌。
- **矫正**：把倾斜车牌摆正、去掉外框，裁成字符完整、方向正常的车牌图。

技术路线：**Python + OpenCV 传统方法**（颜色 + 边缘 + 形态学），可解释、离线可运行，
覆盖蓝/黄/绿/白底车牌与常见 7 位、8 位车牌。不依赖神经网络、不需要训练。

**A 模块的边界**：只负责到「输出摆正的车牌图」为止。
颜色类别的最终判定、字符分割、字符识别、GUI、打包都不在 A 这里（分别属于 B/C/D）。
A 会给一个 `color_hint` 底色**线索**，但那只是参考，最终颜色由 B 判定。


## 1. 目录结构

```
A_plate_detection/
├── plate_common.py        ★ 全组公共契约：数据结构 + 坐标约定 + 图像IO（B/C/D/E 都依赖它）
├── detect_plate.py        ★ 检测定位：detect_plates() → list[PlateRegion]
├── rectify_plate.py       ★ 矫正裁剪：rectify_plates() → list[RectifiedPlate]
├── run_demo.py            独立运行示例（检测+矫正一条龙，命令行）
├── batch_test.py          合成集批量自测 + 生成 docs/定位效果记录.md
├── test_real.py           真实数据集测试 + 生成 docs/真实数据集测试记录.md
├── make_test_images.py    生成合成测试集（带真值标注）
├── make_materials.py      生成讲解素材（流程图/结果对照图）
├── requirements.txt       依赖版本
├── test_images/           14 张合成测试图 + annotations.json（真值）
├── test_real_images/      28 张真实车牌照片（文件名即车牌号真值）
├── test_invalid/          异常输入测试文件（由 batch_test.py 生成）
├── results/               运行输出（标框图、裁剪图、result.json）
│   └── batch/             批量自测的逐图结果
└── docs/
    ├── 定位效果记录.md     指标统计 + 逐图结果 + 异常测试 + 局限
    ├── A模块报告初稿.md    A 的报告内容（方法/实现/结果/问题/改进）
    ├── 流程图.png          讲解素材
    └── 结果对照.png        讲解素材
```

★ 三个文件是 D 集成时真正要 import 的；其余是测试/文档/素材。


## 2. 环境安装

需要 **Python ≥ 3.10**。运行时只依赖 OpenCV 和 NumPy：

```bash
pip install -r requirements.txt
```

`requirements.txt` 内容：

```
opencv-python==4.11.0.86
numpy>=1.26,<3
Pillow>=10.0        # 仅生成测试图/素材用到，纯运行时可不装
```

> D 打包 exe 时以这份版本清单为基线。`plate_common.py` 用了 `dict | None` 语法，
> 需要 Python 3.10+；若组里有人用 3.9，告诉 A，把类型注解改成 `Optional[dict]` 即可。

## 3. 快速开始（独立运行）

任意一张图片，一条命令跑完检测+矫正：

```bash
python run_demo.py test_images/01_normal_blue.jpg
```

输出到 `results/01_normal_blue/`：

| 文件 | 内容 |
|---|---|
| `detected.png` | 原图标框图（绿框 + 序号 + 底色线索 + 得分） |
| `plate_1.png` … | 每块车牌摆正后的裁剪图（**这就是交给 B 的图**） |
| `result.json` | 定位结果 + 矫正尺寸 + 坐标映射矩阵 |

也可以只跑检测或只跑矫正：

```bash
python detect_plate.py  图片路径 --out results   # 只检测，输出标框图+JSON
python rectify_plate.py 图片路径 --out results   # 检测+矫正
```

批量自测（生成效果记录）：

```bash
python make_test_images.py   # 先生成测试集（已生成可跳过）
python batch_test.py         # 跑全量 + 写 docs/定位效果记录.md
```

支持中文路径，例如 `python run_demo.py "D:/我的图片/车牌.jpg"`。


## 4. 接口契约（★ 全组必读，改动需通知 D 和 E）

所有跨模块数据都以 `plate_common.py` 为准。

### 4.1 坐标约定（统一，勿改）

- 所有坐标一律对应**原始输入图像**的像素坐标系：原点左上角，x 向右，y 向下。
- `bbox = (x, y, w, h)`：整数，x/y 为左上角，w/h 为宽高（轴对齐外接框）。
- `quad = [[x,y]×4]`：浮点，四个角点，顺序固定 **左上→右上→右下→左下**（按车牌自身阅读方向，
  即 quad[0]→quad[1] 是车牌长边）。倾斜车牌的 quad 是斜的，bbox 是它的水平外接框。
- 检测内部会缩放图像，但**返回前已换算回原图坐标**，你们拿到的就是原图坐标。

### 4.2 图像格式约定

- 内存中一律为 **OpenCV BGR `uint8` ndarray**，形状 `(H, W, 3)`。
- 交给 B 的车牌裁剪图同样是 BGR `uint8`，已摆正、字符完整、尽量去外框。
- 读图用 `plate_common.load_image(path)`（支持中文路径），不要用 `cv2.imread`（中文路径会失败）。

### 4.3 两个核心数据结构

```python
@dataclass
class PlateRegion:          # detect_plates 的输出，一块车牌候选
    bbox: tuple             # (x, y, w, h) 原图坐标，整数
    quad: list              # [[x,y]×4] 原图坐标，浮点，左上→右上→右下→左下
    angle: float            # 相对水平的倾角（度），范围约 [-45, 45]
    score: float            # 置信度 0~1，越高越可信
    color_hint: str         # 底色线索: blue/yellow/green/white/unknown（仅参考！）

@dataclass
class RectifiedPlate:       # rectify_plates 的输出，一块摆正的车牌
    region: PlateRegion     # 对应的检测区域
    image: np.ndarray       # 摆正后的车牌图 BGR uint8 ← 交给 B
    transform: np.ndarray   # 3×3 单应矩阵：原图齐次坐标 → 矫正图齐次坐标
    # .size 属性返回矫正图 (w, h)
```

### 4.4 两个核心函数

```python
from detect_plate import detect_plates
from rectify_plate import rectify_plates

regions = detect_plates(image_bgr)          # → list[PlateRegion]，按 score 降序
plates  = rectify_plates(image_bgr, regions) # → list[RectifiedPlate]，与 regions 一一对应
```

### 4.5 错误与边界约定

| 情况 | 行为 |
|---|---|
| 图中无车牌 | `detect_plates` 返回 **空列表 `[]`**，不抛异常 |
| 文件不存在 / 类型不支持 / 图片损坏 | `load_image` 抛 **`PlateIOError`**，message 是可直接展示给用户的中文 |
| 超小图 / 空图 | 正常返回 `[]`，不崩溃 |

支持的输入扩展名：`SUPPORTED_EXTS = {.jpg .jpeg .png .bmp .tif .tiff .webp}`（D 的文件对话框过滤器用它）。

### 4.6 JSON 输出格式（run_demo / D / E 共用）

`result.json` 形如：

```json
{
  "num_plates": 1,
  "plates": [
    {"bbox": [284,353,431,131], "quad": [[...],[...],[...],[...]],
     "angle": 0.0, "score": 0.73, "color_hint": "blue"}
  ],
  "image": "test_images/01_normal_blue.jpg",
  "rectified": [
    {"index": 1, "file": "plate_1.png", "size_wh": [444,135],
     "transform": [[...],[...],[...]]}
  ]
}
```


## 5. 给 B 同学（颜色识别 + 字符分割）

**你拿到的东西**：`RectifiedPlate.image`，一块摆正的车牌图（BGR `uint8`）。

```python
from plate_common import load_image
from detect_plate import detect_plates
from rectify_plate import rectify_plates

img = load_image("某图.jpg")
for p in rectify_plates(img, detect_plates(img)):
    plate_bgr = p.image          # ← 你的输入：单块、摆正、BGR
    color_hint = p.region.color_hint  # 底色线索，可作参考但请自己判定颜色
    # 你的 plate_color.py / segment_chars.py 从这里开始
```

关于这块图，你需要知道的：

- **方向**：已摆正，字符水平、阅读顺序从左到右。`quad[0]→quad[1]` 是长边。
- **尺寸**：宽约 160~480px（小牌会放大、大牌会缩小到该范围），高按车牌真实长宽比换算。
  标准牌约 3.14:1，新能源 8 位牌约 3.43:1。**不要假设固定尺寸**，按实际 `p.image.shape` 处理。
- **底色**：蓝/黄/绿/白都可能。`color_hint` 只是 A 的粗略线索（基于外环颜色），
  **最终颜色类别请你自己的 `plate_color.py` 判定**，并对难判情况返回明确状态。
- **边缘**：可能残留 1~3px 的外框/背景边条，你的二值化 + 连通域清理可以去除。
- **字符**：覆盖 7 位和 8 位；字符为窄长形，之间可能有间隔圆点（第 2 位后）。
- **多车牌**：一张图可能返回多块，`rectify_plates` 给你的是一个列表，逐块处理。

**把字符位置映射回原图**（如果 D 要在原图上标字符框）：

```python
import numpy as np
M_inv = np.linalg.inv(p.transform)   # 矫正图坐标 → 原图坐标
# 字符在矫正图中的点 (x,y) → 原图：
pt = M_inv @ np.array([x, y, 1.0])
orig_xy = pt[:2] / pt[2]
```

**与 C 的约定**：字符切片的尺寸/前景背景/排列顺序由 B 和 C 统一，A 不介入；
A 只保证交给 B 的是「单块、摆正、字符完整」的车牌图。


## 6. 给 D 同学（GUI + 集成 + exe 打包）

### 6.1 集成调用（A 部分在你的 pipeline.py 里这样接）

```python
from plate_common import load_image, PlateIOError, SUPPORTED_EXTS
from detect_plate import detect_plates, draw_regions
from rectify_plate import rectify_plates

def run_A(image_path):
    img = load_image(image_path)          # 可能抛 PlateIOError → GUI 弹提示
    regions = detect_plates(img)          # [] 表示无车牌 → GUI 提示"未检测到车牌"
    plates = rectify_plates(img, regions)
    annotated = draw_regions(img, regions)  # 原图标框图，可直接显示在 GUI
    return img, regions, plates, annotated
    # 接下来：for p in plates: 把 p.image 交给 B 的颜色/分割，再交给 C 识别
```

- `draw_regions(img, regions)` 返回画好绿框+序号+得分的原图副本，GUI「原图标框」直接用。
- 每块车牌的裁剪图 `p.image`、颜色线索 `p.region.color_hint`、位置 `p.region.bbox` 都可展示。
- 多车牌：`regions`/`plates` 是列表，GUI 做成可逐个查看（下拉框/列表切换）。

### 6.2 异常处理对照表（A 已覆盖的，GUI 直接捕获）

| 异常 | 来源 | GUI 处理建议 |
|---|---|---|
| 文件不存在 / 错误类型 / 损坏图片 | `load_image` 抛 `PlateIOError` | `try/except PlateIOError as e: 弹窗(str(e))` |
| 未检测到车牌 | `detect_plates` 返回 `[]` | 提示"未检测到车牌，请换一张" |
| 取消选图 | GUI 层 | 文件对话框返回空时直接 return |
| 中文路径 | `load_image` 已用 `np.fromfile` 兼容 | 无需额外处理 |

> B/C 模块各自的失败（颜色难判、分割异常、识别失败）由它们的接口返回状态，D 统一兜底。
> A 保证：无论输入如何，`detect_plates` 不会抛异常（只返回 list），读图异常集中在 `load_image`。

### 6.3 打包注意（PyInstaller）

- A 模块**纯 Python + OpenCV + NumPy**，无模型文件、无外部资源，打包简单。
- 依赖见 `requirements.txt`；`opencv-python` 会被 PyInstaller 自动收集。
- `plate_common.py` / `detect_plate.py` / `rectify_plate.py` 三个文件随源码打包即可。
- A **不读任何运行时外部文件**（测试图/字体只在生成素材时用，不进 exe），
  所以发行目录无需为 A 额外带资源。字符库等资源是 C 的，由 C/D 负责纳入。
- 若打包后中文路径仍异常，确认用的是 `load_image` 而非 `cv2.imread`。

### 6.4 给 C 同学（间接交接）

A 不直接对接 C。A → B（车牌图）→ C（字符切片）。
C 需要的「字符归一化尺寸、HOG 特征、字符库」都建立在 B 的分割输出上，与 A 无直接接口。
A 唯一可能帮到 C 的：`p.transform` 可把任意矫正图坐标映射回原图（见 §5）。


## 7. 给 E 同学（数据 + 测试 + 评估）

### 7.1 定位评估接口

A 的检测输出可直接喂给你的 `evaluate.py`：

```python
regions = detect_plates(img)
for r in regions:
    r.bbox        # (x,y,w,h) 原图坐标，与你的标注同坐标系，可直接算 IoU
    r.quad        # 四角点，需要旋转框指标时用
    r.angle       # 倾角，可评估矫正角度误差
    r.score       # 置信度，可用于画 PR 曲线 / 调阈值
    r.color_hint  # 底色线索（注意：最终颜色指标应以 B 的输出为准）
```

### 7.2 真值标注格式（A 的测试集已用，建议全组沿用）

`test_images/annotations.json`：

```json
{
  "01_normal_blue.jpg": {
    "plates": [
      {"bbox": [280,350,440,140], "text": "京A12345", "color": "blue"}
    ]
  },
  "12_no_plate.jpg": {"plates": []}
}
```

- 无车牌图片 `plates` 为空列表。
- 你扩充真实照片标注时，建议再加 `angle`（真值倾角）字段，便于评估矫正角度误差。
- **数据划分**：A 的合成测试集仅用于开发自测；你构建字符库/最终测试的真实图片请独立划分，
  避免与开发样本重复（分工文件要求字符库样本与最终测试样本分开）。

### 7.3 指标口径（batch_test.py 已实现，可复用）

- 匹配：预测框与真值框 **IoU ≥ 0.5** 记为命中（贪心，按 score 降序）。
- 检出率 recall = 命中真值数 / 真值总数；精确率 precision = 命中预测数 / 预测总数。
- 平均 IoU = 命中对 IoU 均值。
- 运行 `python batch_test.py` 自动生成 `docs/定位效果记录.md`（含逐图结果+异常测试+局限）。

### 7.4 测试结果（供报告引用）

**合成集**（14 图 / 14 块真值牌）：recall 100%、precision 93.3%、平均 IoU 0.953，
单图平均检测耗时约 40ms（CPU）。无车牌图正确返回空，异常输入全部正确拦截。
（唯一误检是 `11_distractor` 中形似车牌的蓝底白字广告牌文字行，属传统方法硬案例。）

**真实照片集**（28 张，文件名即车牌号真值，见 `docs/真实数据集测试记录.md`）：
**单牌正确检出 26/28，漏检 2，多检 0**。覆盖绿牌(新能源8位)/正常蓝牌/倾斜牌/黄牌四组。
漏检的 2 张（皖A037G9、皖AX910B）为小幅面+透视畸变+低对比+纹理背景，属传统方法能力边界。
运行 `python test_real.py --dir <真实图目录>` 复测，生成对照图与记录。


## 8. 算法原理（讲解/报告用）

### 8.1 检测定位 `detect_plate.py`

双通道找候选，再层层筛选：

1. **预处理**：长边缩到 ≤1024（加速，坐标最后换算回原图）；转 HSV 和灰度。
2. **颜色通道**：对蓝/黄/绿/白各做 HSV 阈值掩码，小核形态学闭运算连成块，取轮廓的最小外接旋转矩形。
3. **边缘通道**：灰度 → 双边滤波 → Sobel 竖直边缘 → Otsu 二值化 → 横向闭运算，
   把字符的竖直边缘连成块（车牌字符区竖直边缘密集）。
4. **几何筛选**：长宽比 1.7~4.8（标准牌 3.14、新能源 3.43，透视畸变可低至 1.7）、
   最小尺寸 45×12px、倾角 ≤45°。颜色通道额外允许宽条（ratio≤6.5）进入以便收紧。
5. **收紧**：
   - 用底色掩码把粗框收紧到真实牌面；掩码填充率低（L 形粘连）或过宽时，
     用「字符边缘活动范围」反推整牌（字符带约占领牌宽 95%，牌高按标准长宽比反推）。
   - **宽条专用**（ratio>4.8 的颜色候选，车牌与同色草丛/背景粘成宽条）：
     滑动窗口用连通域字符数定位车牌子区域，再外扩边距覆盖整牌两端字符。
6. **底色门槛**：底色覆盖率 ≥0.30 且外环底色线索非 unknown（真实牌必有明确底色）；
   白牌候选另要求有黑色字符结构（暗字占比 0.06~0.55）且字符数 ≥5，排除白色引擎盖/天空。
7. **字符验证**（核心判别，区分车牌与有色背景）：
   - **连通域字符数 ≥3**（统计字符形状连通域，真实牌 6~10，背景色块/广告牌大字/碎片 ≤2）；
   - 字符峰数 4~18（水平投影找峰，辅助）；
   - 字符带高度占比 ≥0.40（排除字符只占中间一小段的整块广告牌）。
8. **评分**：底色覆盖率 + 长宽比接近度（高斯 σ=0.7）+ 字符数接近度 + 纹理 + 边缘密度 加权。
9. **NMS 去重**：IoU>0.3 或包含关系去重；重叠时优先保留颜色通道整牌框；
   并抑制「相对主牌极小且字符少」的碎片（车身小贴纸），保留正常多车牌。

### 8.2 矫正裁剪 `rectify_plate.py`

1. quad 外扩 12%（防切字，等比放大不改变长宽比）→ 透视变换摆正到标准朝向，宽 160~480。
2. 字符连通域拟合残余倾角，做小角度旋转微调（0.6°~15° 才调）。
3. 按底色一致性裁掉四周外框/铆钉边条（每侧最多裁 15%，裁太多则放弃）。
4. 三步变换复合为 `transform`（3×3 单应矩阵），保留与原图的坐标对应关系。

## 9. 可调参数（调参改这里，别散落各处）

`detect_plate.py` 顶部：

| 参数 | 默认 | 含义 |
|---|---|---|
| `DETECT_LONG_SIDE` | 1024 | 检测前长边缩放上限 |
| `MIN_PLATE_W / MIN_PLATE_H` | 45 / 12 | 原图中车牌最小宽/高（px） |
| `RATIO_RANGE` | (1.7, 4.8) | 最终验收长宽比（含透视/新能源宽牌） |
| `RATIO_INIT` | (1.7, 4.8) | 初筛长宽比（颜色通道宽条另放宽到 6.5） |
| `IDEAL_RATIO / RATIO_SIGMA` | 3.2 / 0.7 | 评分理想长宽比 / 高斯宽度 |
| `MIN_COLOR_RATIO` | 0.30 | 底色覆盖率门槛 |
| `SCORE_THRESH` | 0.45 | 综合得分阈值（低于丢弃） |
| `NMS_IOU` | 0.3 | 去重 IoU 阈值 |
| `MAX_PLATES` | 8 | 单图最多返回车牌数 |
| `FULL_WIDTH_FRAC` | 0.95 | 超此图宽比例视为背景色带拒绝 |
| `COLOR_RANGES` | 见源码 | 各底色 HSV 范围（蓝色已放宽 S/V 覆盖褪色牌） |

`rectify_plate.py` 顶部：`EXPAND`(1.12)、`TARGET_W_MIN/MAX`(160/480)、
`FINE_ANGLE_MIN/MAX`(0.6/15)、`TRIM_FRAC`(0.88)、`TRIM_LIMIT`(0.15)。

> 真实照片上若漏检多，先试降 `SCORE_THRESH`、放宽 `COLOR_RANGES`；误检多则反向。
> 调参后跑 `python batch_test.py`（合成）和 `python test_real.py`（真实）看指标变化。


## 10. 已知局限（基于真实数据集实测）

| 类别 | 说明 | 缓解方向 |
|---|---|---|
| 小幅面+透视+纹理背景 | 真实集漏检的 2 张（皖A037G9、皖AX910B）：牌小(~140px)、透视畸变、低对比、周围车身纹理干扰，颜色掩码碎片化 | 神经网络检测（作业说明神经网络测试要求更高） |
| 大倾角/透视 | 支持平面旋转 \|倾角\|≤45°，透视畸变未完整建模 | 四边形透视矫正 |
| 同色草丛粘连 | 绿牌与绿背景粘成宽条时靠字符窗口收紧，个别牌末位字符可能略切 | 已尽量外扩边距，B 可再清边 |
| 强反光/过曝 | 底色 HSV 偏移、字符边缘被高光淹没 | 放宽颜色范围 / 自适应直方图均衡 |
| 双层牌 | 字符验证按单层 7/8 位设计 | 作业聚焦单层牌 |
| 裁剪边缘 | 可能残留少量背景/边框 | B 二值化/连通域清理 |

详见 `docs/定位效果记录.md`（合成）与 `docs/真实数据集测试记录.md`（真实）。

## 11. 验证与复现

```bash
python make_test_images.py   # 生成 14 张合成测试图 + 真值
python batch_test.py         # 合成集全量自测 → docs/定位效果记录.md + results/batch/
python test_real.py --dir <真实图目录>  # 真实集测试 → docs/真实数据集测试记录.md + results/real/
python make_materials.py     # 生成 docs/流程图.png、docs/结果对照.png
```

合成集覆盖：正常蓝牌、±倾斜、黄牌、新能源绿牌(8位)、白色警牌、多车牌(3块)、
小车牌、模糊、低光照、干扰广告牌、无车牌(2种)、大倾角30°。
异常输入覆盖：错误类型、伪装扩展名、损坏/截断图片、不存在文件、超小图。
真实集覆盖：绿牌/正常蓝牌/倾斜牌/黄牌四组各 7 张（文件名即车牌号真值）。

## 12. A 模块交付清单对照（分工文件要求）

| 分工要求 | 对应文件 | 状态 |
|---|---|---|
| 检测定位代码 `detect_plate.py` | `detect_plate.py`（坐标对应原图，无车牌返回空） | ✅ |
| 矫正裁剪代码 `rectify_plate.py` | `rectify_plate.py`（保留原图坐标映射 transform） | ✅ |
| 独立运行示例 | `run_demo.py`（指定图片即可运行，保存标框+裁剪） | ✅ |
| 定位效果记录 | `docs/定位效果记录.md` + `docs/真实数据集测试记录.md` | ✅ |
| 本模块报告内容及讲解素材 | `docs/A模块报告初稿.md` + `流程图.png` + `结果对照.png` | ✅ |
| 交接：裁剪图→B / 接口→D / 定位结果→E | 见 §5 / §6 / §7 | ✅ |

**给 E 的实际贡献说明（可直接引用）**：A 完成了车牌检测、定位、倾斜矫正与裁剪模块，
实现颜色+边缘+形态学双通道检测、连通域字符验证、底色门槛、宽条字符窗口收紧、NMS 去重、
透视矫正与坐标映射；搭建全组公共接口契约 `plate_common.py`；构建 14 张合成测试集与批量自测脚本，
并用 28 张真实车牌照片验证（单牌正确检出 26/28，多检 0）；提供独立运行示例、效果记录、报告初稿与讲解素材。
