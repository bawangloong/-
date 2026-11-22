# 车牌识别系统 · D 模块（GUI 与系统集成）

课程大作业《车牌识别系统》中 **D 同学**负责的部分：把 A（检测/矫正）、
B（颜色/字符分割）、C（字符库识别）串成完整流程，提供图形界面、异常处理、
离线发行包和运行说明。

> 本目录同时是**可独立运行的完整系统**：A 模块未交付时使用内置的传统检测/矫正
> 兜底实现，接口按 `docs/A模块接口约定.md` 预留，A 的代码放入 `vendor/a_plate/`
> 后会自动接管，无需改动 GUI。

## 一、快速开始

### 1. 直接运行 exe（推荐给老师和同学）

解压后双击 `车牌识别系统.exe`。程序自带 Python 运行时，**目标电脑不需要安装
Python、OpenCV 或任何依赖**，也不需要联网。

### 2. 源码运行（开发调试）

```bash
pip install -r requirements.txt
python main.py            # 启动 GUI
```

环境要求：Windows 10/11 64 位，Python 3.13，依赖见 `requirements.txt`。

### 3. 命令行批量识别

```bash
python -m app.cli samples/normal_blue.png
python -m app.cli samples/*.png --out results          # 导出图 + JSON
python -m app.cli samples/multi_two.png --json         # 只输出 JSON
```

## 二、功能一览

- 选择本地图片（JPG / PNG / BMP / TIF / WEBP），支持中文路径；
- 自动检测一张图中的**多块车牌**，倾斜车牌透视矫正；
- 输出每块车牌的**颜色、字符数量、字符分割图、逐字符匹配分和完整号码**；
- 界面展示“原图标框、车牌裁剪、二值化、字符框、逐个字符切片”；
- 多车牌用列表逐个切换查看；
- 识别在后台线程执行，界面不卡死，可取消；
- 覆盖取消选图、错误类型、损坏图片、无车牌、字符数异常、模块失败等情况；
- 一键导出标框图、过程四联图、字符切片和 JSON 结果。

## 三、目录结构

```
plate_system/
├── 车牌识别系统.exe        # 绿色启动器（由 build/make_portable.ps1 生成）
├── app_main.py             # 绿色包入口（异常写日志并弹窗）
├── main.py                 # 源码 / PyInstaller 入口
├── app/
│   ├── runtime.py          # 路径、图片读取（中文路径/EXIF）、异常、日志
│   ├── detector.py         # 内置检测+矫正兜底；A 模块适配器
│   ├── plate_utils.py      # 去外框、标框、过程四联图
│   ├── pipeline.py         # 统一流水线与结果结构
│   ├── export.py           # 结果导出
│   ├── gui.py              # Tkinter 界面
│   ├── cli.py              # 命令行入口
│   └── main.py             # GUI 启动
├── vendor/
│   ├── b_plate/            # B：plate_color.py、segment_chars.py
│   └── c_char/             # C：HOG 特征、字符库、recognize_chars.py
├── samples/                # 合成演示图（正常/倾斜/多车牌/无车牌/新能源/模糊/黑牌/大图）
├── tests/                  # 回归测试
├── tools/                  # 生成演示图、冒烟测试、GUI 截图
├── build/                  # PyInstaller spec、绿色包脚本、启动器源码
├── docs/                   # D 部分报告、操作说明、接口约定、测试记录
├── requirements.txt
└── README.md
```

## 四、验证

```bash
python -m unittest discover -s tests -v     # 6 项回归测试
python tools/smoke_test.py                  # 8 张演示图逐张打印结果
```

当前演示图结果（合成数据，仅验证流程与工程实现）：

| 图片 | 车牌数 | 号码 | 颜色 | 字符数 | 单图耗时 |
|---|---|---|---|---|---|
| normal_blue.png | 1 | 京A12345 | 蓝 | 7 | ~145 ms |
| tilt_yellow.png | 1 | 粤B88888 | 黄 | 7 | ~81 ms |
| multi_two.png | 2 | 沪AD12345 / 京A12345 | 绿 / 蓝 | 8 / 7 | ~131 ms |
| green_8.png | 1 | 沪AD12345 | 绿 | 8 | ~77 ms |
| black_plate.png | 1 | 蒙A88888（真值京A88888） | 黑 | 7 | ~79 ms |
| large_3000.jpg | 1 | 京A12345 | 蓝 | 7 | ~128 ms |
| no_plate.png | 0 | — | — | — | ~35 ms |
| blur_glare.png | 0（漏检） | — | — | — | ~33 ms |

## 五、说明与边界

- `vendor/` 中 B、C 的代码来自组员交付，仅做了两处**最小集成改动**：
  C 的相对导入兼容、B 的 `min_char_width_ratio` 可选参数（默认值保持原行为，
  用于避免数字“1”被当成噪点删除）。改动原因见 `docs/D部分报告.md`。
- 内置检测是 D 的兜底实现，精度不能替代 A 的正式算法；模糊、反光、与车身同色
  的车牌仍可能漏检。
- 详细操作见 `docs/操作说明.md`，报告见 `docs/D部分报告.md`。
