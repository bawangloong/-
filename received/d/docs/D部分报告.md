# D 部分报告：GUI、系统集成与 exe 打包

> 课程大作业《车牌识别系统》· D 同学
> 对应交付：统一识别入口、GUI、异常处理、环境与打包、exe 发行包、跨机运行记录、操作说明。

## 1. 任务与完成情况

D 的职责不是再写一个识别算法，而是把 A（检测/矫正）、B（颜色/分割）、C（字符库
识别）变成一个**普通用户能直接使用**的完整程序，并保证换一台没有 Python 的
Windows 电脑也能运行。

| 交付项 | 状态 | 位置 |
|---|---|---|
| 统一识别入口 `pipeline.py` | 完成 | `app/pipeline.py` |
| GUI 程序 | 完成 | `app/gui.py` |
| 异常处理 | 完成 | `app/runtime.py`、`app/gui.py` |
| 环境与打包文件 | 完成 | `requirements.txt`、`build/plate_app.spec` |
| 完整 exe 发行包 | 完成（绿色运行时方案） | `dist/车牌识别系统/` |
| 另一台 Windows 电脑运行记录 | 本机干净环境已验证，第二台电脑待复测 | `docs/另一台电脑测试记录.md` |
| 操作说明 | 完成 | `docs/操作说明.md` |

## 2. 系统总体流程

```
用户选图
   │
   ▼
read_image_bgr（Pillow 解码，支持中文路径、EXIF 摆正）
   │
   ▼
A：检测 detect_plates(image) ──► 0..N 个候选框（原图坐标）
   │                               │
   │                          无车牌 → 统一提示
   ▼
A：矫正 rectify_plate(image, plate) ──► 正向车牌图
   │
   ▼
B：颜色 classify_plate_color(crop)
   │
   ▼
B：分割 segment_plate(crop, debug=True) ──► 字符图（40×20，白字黑底）+ 位置
   │
   ▼
C：CharacterRecognizer.recognize_chars(chars, layout)
   │        7/8 位 → standard（首位省份、第二位字母）
   │        其它   → unrestricted（保留结果但提示异常）
   ▼
统一结果 dict ──► GUI 展示 / 导出 PNG+JSON / 命令行
```

一次识别内所有模块共享同一份原图与坐标，D 只做数据转换和错误隔离，不改各模块
内部算法。单块车牌失败不会中断其它车牌。

## 3. 统一接口与数据结构

### 3.1 检测接口

D 不直接调用 A 的函数名，而是通过 `app/detector.py` 的适配层：

- `FallbackBackend`：A 未交付时的内置传统检测（HSV 底色 + 梯度纹理 + 透视矫正）；
- `ABackend`：加载 `vendor/a_plate/detect_plate.py` 和 `rectify_plate.py`；
- 启动时按“环境变量 `PLATE_A_DIR` → `vendor/a_plate/` → 内置”的顺序选择。

这样 A 的代码到位后只需放文件，GUI 和测试代码一行不用改。接口约定见
`docs/A模块接口约定.md`。

### 3.2 结果结构

`PlatePipeline.recognize_image()` 返回：

```text
{
  ok, source, image_size, plate_count, rejected,
  timings: {read_ms, detect_ms, total_ms, recognize_ms},
  warnings: [...],
  error: null | {code, message},
  plates: [{
    index, bbox, quad, detect_score, source,
    crop（BGR 数组，仅 GUI 用）,
    color: {color, label, confidence, detail},
    segmentation: {count, status, boxes, message},
    recognition: {text, status, characters:[{position,label,similarity,candidates}]},
    chars（40×20 数组，仅 GUI 用）, views: {norm, binary},
    text, confidence, status, warnings,
    timings: {rectify_ms, color_ms, segment_ms, recognize_ms, total_ms}
  }]
}
```

`result_to_json()` 会剥掉 numpy 图像，保证可以直接 `json.dumps`，导出和 E 的
评估脚本复用同一结构。

### 3.3 对 B、C 的集成改动（最小改动）

| 改动 | 原因 | 是否影响原行为 |
|---|---|---|
| C 的 `recognize_chars.py`、`build_library.py` 增加 `try: 相对导入 / except: 原导入` | 让 C 既能在自己目录独立运行，也能被 D 作为包导入、被 PyInstaller 打包 | 否，原运行方式不变 |
| B 的 `segment_plate()` 增加可选参数 `min_char_width_ratio`，默认 0.25 | 原实现会把宽度小于 1/4 标准字符宽的块当噪点删掉，数字“1”恰好被删；D 集成时传 0.10 | 否，默认值等于原逻辑 |

第 2 处改动来自实际测试：新能源车牌 `沪AD12345` 只切出 7 个字符，缺“1”。
定位到 `ww < 0.25 * target_w` 后，用可选参数保留原默认行为，D 侧传 0.10，
修复后 8 个字符全部切出且识别正确。

另外，D 在交给 B 之前增加了 `strip_plate_frame()`：当 A 的裁剪把车牌白色外框
带进来、外框又不贴图像边缘时，B 的“删除贴边连通域”无法去掉内框，投影会被
一条横线连成一片。D 先识别“又宽又高/细长条且靠近边缘”的连通域并抹成底色，
再交给 B，避免修改 B 的算法。

## 4. GUI 实现

技术选型：**Tkinter + Pillow**。理由：

- Python 标准库自带，不增加打包体积和第三方依赖；
- Windows 上字体、缩放、文件对话框表现稳定；
- 对“选图—识别—看结果”这类单窗口工具足够，不需要 Electron/Qt 的复杂度。

### 4.1 布局

- 顶部：标题栏 + 工具栏（选择图片/开始识别/取消/保存结果/打开结果目录 + 进度条）；
- 左侧：原图 Canvas（自动等比缩放，识别后画绿色四边形和序号/号码）；
- 左下：车牌列表，多车牌逐个切换；
- 右侧 Notebook：
  - 识别结果：大号号码、颜色徽标、字符数/平均分/耗时/状态、逐字符切片和匹配分；
  - 处理过程：车牌裁剪 → 二值化 → 字符框 → 字符切片四联图；
  - 运行日志：带时间戳的操作与错误记录。

### 4.2 多车牌

检测结果按 `index` 生成按钮，点击切换 `selected`，结果页、过程图、字符网格
同步刷新；每块车牌有独立的颜色、字符数、号码、警告和耗时。

### 4.3 线程模型（界面不卡）

```text
主线程：Tk 事件循环
  └─ 点击开始识别 → 禁用按钮 → 启动 worker 线程
worker：pipeline.recognize_file(path, progress=cb)
  └─ progress 回调 → queue.put(("progress", stage, frac, detail))
主线程：after(80ms) 轮询 queue → 更新进度条/状态 → 完成后刷新界面
```

- 所有 Tk 控件只在主线程操作，worker 不碰界面；
- 取消：主线程置 `cancel_flag`，worker 在下一个进度回调抛 `Cancelled`，
  主线程恢复按钮；
- 未预期异常：worker 捕获后把 traceback 放入 queue，界面弹窗并写
  `logs/plate_app.log`，不会出现“点了没反应”。

### 4.4 图像显示

原图、车牌、字符都是 numpy BGR，统一经 `Image.fromarray(RGB)` 转
`ImageTk.PhotoImage`；Canvas 尺寸变化时按 `fit_to_box()` 重新等比缩放。
字符切片用最近邻放大 3 倍，避免二值边缘被插值糊掉。

## 5. 异常处理

D 把异常分成“用户可理解”和“程序内部”两类，前者有稳定错误码，便于测试断言：

| 场景 | 错误码 / 处理 |
|---|---|
| 取消文件对话框 | 直接返回，日志记录，不弹错 |
| 扩展名不是图片 | `unsupported_type`，弹窗提示支持格式 |
| 文件不存在 / 不是文件 | `file_not_found` / `not_a_file` |
| 0 字节 | `empty_file` |
| 损坏图片、伪扩展名 | `decode_failed`（Pillow 解码异常） |
| 图片过小 | `image_too_small` |
| 未检测到车牌 | `no_plate`，提示换图，不算崩溃 |
| 字符库缺失/损坏 | `library_missing` / `library_invalid`，启动时提示重新解压 |
| 单块车牌矫正/分割/识别失败 | 该块记 `warnings` 并继续处理下一块 |
| 字符数不是 7/8 | `count_abnormal`，用 unrestricted 仍识别，界面提示复核 |
| 识别中退出 | 二次确认，取消 worker 后退出 |
| 未预期异常 | 弹窗 + 完整 traceback 写日志 |

读取图片特意用 Pillow 而不是 `cv2.imread`：后者在 Windows 中文路径下会静默
返回 `None`，是课程作业里最常见的“换台电脑就不能用”的原因之一。保存图片
用 `cv2.imencode(...).tofile()` 同理。

## 6. 打包与运行环境

### 6.1 环境

| 项目 | 版本 |
|---|---|
| Windows | Windows 11 家庭中文版 25H2（build 26200） |
| Python | 3.13.7（64 位） |
| numpy | 2.3.5 |
| opencv-contrib-python | 5.0.0.93 |
| Pillow | 12.0.0 |
| PyInstaller | 未安装（本机无外网，见 6.3） |

### 6.2 资源路径

`app/runtime.py` 区分两种运行方式：

- 源码：项目根目录 = `app/` 上一级；
- 打包：只读资源在 `sys._MEIPASS`（PyInstaller）或 exe 同级目录（绿色包），
  可写目录（`results/`、`logs/`）固定在 **exe 所在目录**，不会写进临时解包目录。

字符库通过显式路径传入 `CharacterRecognizer`，避免依赖当前工作目录。

### 6.3 两种发行方式

**方式 A：PyInstaller（课程推荐的常规方案）**

`build/plate_app.spec` 已写好：入口 `main.py`，把 `vendor/c_char/character_library`
作为 data 带入，隐藏导入 `PIL._tkinter_finder`，生成 `dist/车牌识别系统/`。
在有网环境执行：

```bash
pip install pyinstaller
pyinstaller build/plate_app.spec --noconfirm --clean
```

本机执行 `pip download pyinstaller` 时 PyPI 与国内镜像均被网络策略拦截
（TLS 连接被关闭 / HTTP 403），无法安装 PyInstaller。

**方式 B：自带 Python 运行时的绿色包（本次实际交付）**

用 `build/make_portable.ps1` 组装：

```
车牌识别系统/
├── 车牌识别系统.exe      # C# 启动器（csc 编译，双击即用）
├── app_main.py           # 入口，启动异常弹窗 + 写 logs/startup_error.log
├── app/ vendor/ samples/ docs/
└── runtime/              # Python 3.13 + numpy/OpenCV/Pillow + Tcl/Tk
```

启动器只做一件事：用 `runtime\pythonw.exe` 运行 `app_main.py`，工作目录设为
exe 所在目录。目标电脑不需要安装 Python，也不需要联网。代价是体积较大
（约 211 MB，压缩后约 82 MB），但换机最稳、和开发环境完全一致。

为减小体积，删除了 `cv2/opencv_videoio_ffmpeg500_64.dll`（约 30 MB，图片
识别用不到视频编解码）；如果以后要加视频输入，把这个 DLL 放回即可。

### 6.4 发行目录完整性

exe 依赖以下内容，缺一不可：

- `runtime/`（Python 解释器 + 依赖 + Tcl/Tk）
- `app/`、`vendor/c_char/character_library/library.npz`
- `samples/`（可选，演示用）
- 同级的 `app_main.py`

`app_main.py` 在启动失败时会把 traceback 写到 `logs/startup_error.log` 并弹窗，
避免 windowed 程序“双击没反应”。

## 7. 测试与结果

### 7.1 合成演示图（8 张）

用 `tools/make_demo_images.py` 生成正常、倾斜、多车牌、无车牌、新能源 8 位、
模糊反光、黑牌、3000×2000 大图八类场景。结果：

| 图片 | 车牌数 | 识别号码 | 颜色 | 字符数 | 耗时 |
|---|---|---|---|---|---|
| normal_blue.png | 1 | 京A12345 | 蓝 | 7 | 145 ms |
| tilt_yellow.png | 1 | 粤B88888 | 黄 | 7 | 81 ms |
| multi_two.png | 2 | 沪AD12345 / 京A12345 | 绿 / 蓝 | 8 / 7 | 131 ms |
| green_8.png | 1 | 沪AD12345 | 绿 | 8 | 77 ms |
| black_plate.png | 1 | 蒙A88888（真值京A88888） | 黑 | 7 | 79 ms |
| large_3000.jpg | 1 | 京A12345 | 蓝 | 7 | 128 ms |
| no_plate.png | 0 | — | — | — | 35 ms |
| blur_glare.png | 0（漏检） | — | — | — | 33 ms |

统计：有车牌的 7 张图中检出 6 张（85.7%）；检出的 7 块车牌中 6 块号码完全
正确（85.7%），字符数 7/7 正确。以上为合成图，仅验证工程链路，不代表真实
路测精度。

### 7.2 异常与回归测试

`python -m unittest discover -s tests -v`：6 项全部通过。

| 用例 | 结果 |
|---|---|
| 蓝牌识别 | 通过，京A12345 / 7 字符 |
| 新能源 8 位 | 通过，沪AD12345 |
| 无车牌 | 通过，返回 `no_plate` |
| 非图片类型 `.txt` | 通过，`unsupported_type` |
| 损坏 PNG | 通过，`decode_failed` |
| 中文目录 + 中文文件名 | 通过，正常识别 |

GUI 侧用 `tools/gui_smoke.py` 注入图片和结果并截图，验证布局、多车牌切换、
字符网格和颜色徽标；取消、错误弹窗等交互按 `docs/测试记录_D模块.md` 手工
检查。

### 7.3 性能

1280×800 图片单块车牌约 80~150 ms，3000×2000 约 130 ms；主要耗时在字符
分割（B 的纯 Python 连通域，40~70 ms）和识别（7 个字符约 20~30 ms）。
界面用后台线程，识别期间仍可拖动和取消。

## 8. 问题与改进

| 问题 | 现象 | 处理 | 后续建议 |
|---|---|---|---|
| A 模块未交付 | 没有 `detect_plate.py` | 写内置兜底 + 适配层，A 到位自动接管 | A 交付后替换并复测 |
| 数字“1”被删 | 8 位车牌只切 7 个 | B 增加可选最小宽度参数，D 传 0.10 | 建议 B 在正式版默认调低 |
| 车牌内框残留 | 分割出 5 个“字符”，实际是框线 | D 增加 `strip_plate_frame()` | A 裁剪时收紧到框内 |
| 绿牌只覆盖下半 | 候选框过矮/过高 | 按 3.14 宽高比只补短边 | 真实渐变牌需再调 |
| 绿牌与绿色车身同色 | 候选框把车身并进来 | 合成图把第二辆车改灰色规避 | 真实场景需 A 用纹理/边缘分割 |
| 模糊 + 强反光白牌 | 漏检 | 记录为失败案例 | 增加多尺度/去反光预处理 |
| 京/蒙混淆 | 黑牌识别成蒙A88888 | 记录为 C 的形近字案例 | C 增加省份上下文约束 |
| 第二台电脑复测 | 本机干净 PATH 已验证 | 待在有第二台机器时补 | 按记录表逐项打勾 |

## 9. 分工与实际贡献

D 的实际工作：

1. 统一接口设计：结果结构、错误码、进度回调、A 模块适配层；
2. 将 B、C 代码接入并处理两处兼容问题（相对导入、数字“1”宽度）；
3. 实现 `strip_plate_frame()` 解决内框残留；
4. 完成 Tkinter GUI、多车牌切换、过程图/字符网格、线程与取消；
5. 完成图片读取/保存的中文路径与 EXIF 处理；
6. 完成 8 张演示图生成、6 项回归测试、错误场景测试；
7. 完成绿色发行包（启动器 + 自带运行时）与 PyInstaller 配置；
8. 编写操作说明、接口约定、环境与打包说明、测试记录和本报告。

参与联调：与 B 确认 40×20 白字黑底约定；与 C 确认 `recognize_chars` 输入
顺序和 `standard/unrestricted` 两种 layout；与 E 约定 JSON 导出字段。

## 10. 交付清单对照

| 要求 | 对应文件 |
|---|---|
| 统一识别入口 | `app/pipeline.py` |
| GUI | `app/gui.py`、`main.py` |
| 异常处理 | `app/runtime.py`、`app/gui.py` 第 5 节 |
| 依赖清单 | `requirements.txt` |
| 启动方法 | `README.md`、`docs/操作说明.md` |
| PyInstaller 配置 | `build/plate_app.spec`、`build/build_exe.ps1` |
| exe 发行包 | `dist/车牌识别系统/`（由 `build/make_portable.ps1` 生成） |
| 跨机运行记录 | `docs/另一台电脑测试记录.md` |
| 操作说明 | `docs/操作说明.md` |
| 本模块报告 | 本文件 |
| 展示素材 | `docs/gui_screenshot.png`、`docs/gui_process.png`、`docs/demo_result/` |
