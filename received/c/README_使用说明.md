# C 部分使用说明

## 1. 这份交付可以做什么

输入一组已分割、按从左到右排列的字符切片，输出车牌文字、每字 Top3 候选、相似度和复核状态。
支持 65 类：10 个数字、排除 I/O 的 24 个大写字母、31 个省份简称。
已接入你提供的 B 模块，原始文件放在 `integration/B_original`，没有修改 B 的代码。
日常识别、构库和评估均可离线运行；字符库和图片已随包附齐，不需要训练神经网络，也不需要 GPU。

## 2. 在当前电脑立即运行

在 PowerShell 打开本文件所在文件夹：

```powershell
Set-Location 'D:/课程文件/视频多媒体检索实践/车牌识别_C部分交付/plate_char_C'
& 'D:/应用/python.exe' './integration_example.py'
```

这条命令会真实调用 B 的颜色判断和分割，再调用 C。结果在 `results/B_integration`：

- `summary.csv` / `summary.json`：六张图的汇总。
- `blue_7.json` 等：每张图的颜色、框、分割状态、识别结果。
- `*_matches.png`：输入、归一化和 Top3 样本对照图。
- `*_chars/`：本次重新分割的切片。

预期五张正常样例分别输出 `浙FA1B2C`、`京A12345`、`粤CD12345`、`苏E66T78`、`沪B88888`。
倾斜图只分出 5 个字符，返回 `invalid_length`，应交 A 先矫正。它不会输出一个伪造的 7 位号码。
这些图是 B 生成的合成图，正常五张全部匹配也不能代表真实道路整牌准确率。

## 3. 换一台电脑

建议使用 Python 3.11-3.13；实际验证版本见第 10 节。已有兼容环境可直接复用。
在解压目录创建独立环境，不修改全局 Python：

```powershell
py -3.13 -m venv .venv
& './.venv/Scripts/python.exe' -m pip install -r requirements.txt
& './.venv/Scripts/python.exe' './integration_example.py'
```

如果没有 3.13，可把第一行换为本机 Python 的完整路径。安装依赖需要联网，之后可离线识别。
仅需 NumPy、OpenCV 和 Pillow；无需 scikit-learn、PyTorch 或 pytest。

## 4. 识别 B 已经保存的字符目录

```powershell
& 'D:/应用/python.exe' './recognize_chars.py' --chars-dir './integration/B_original/output/blue_7_chars' --output './results/local_blue.json' --visualize './results/local_blue.png'
& 'D:/应用/python.exe' './recognize_chars.py' --chars-dir './integration/B_original/output/green_8_chars' --output './results/local_green.json'
```

文件按自然顺序排列：`char_01.png`、`char_02.png`……`char_10.png`，请避免混入其他图片。
输入为原始整块车牌时，应先让 B 分割，不能把整牌直接当作单字输入。

## 5. 识别单个字符

```powershell
& 'D:/应用/python.exe' './recognize_chars.py' --image './integration/B_original/output/blue_7_chars/char_01.png' --charset province --visualize './results/local_one.png'
```

`--charset` 可为 `all`、`province`、`letter`、`alnum`；默认 all。
`--layout unrestricted` 用于任意长度字符序列诊断，不做常见车牌位置约束。
`--output` 保存 UTF-8 JSON；`--visualize` 额外生成 PNG。

## 6. 接 A 提供的新车牌图

```powershell
& 'D:/应用/python.exe' './integration_example.py' --image 'D:/你的文件夹/已矫正车牌.png' --output './results/local_real_plate'
```

输入应为单块裁切且已矫正的车牌；整车图先交 A 检测定位。该入口不会自动做检测或矫正。
自带合成样例以外的输入不自动填写真值，`evaluation_only.truth` 为 null；需要 E 另行标注后评估。

## 7. 添加样本与重新构库

训练目录是 `character_library/train/<标签>/图片`，例如 `A`、`5`、`zh_jing`（京），也支持直接以汉字建目录。
完整映射见 `labels.py`。把人工确认标签的**训练图片**放到对应目录，检查清楚后执行：

```powershell
& 'D:/应用/python.exe' './build_library.py' --output './character_library/library_custom.npz'
& 'D:/应用/python.exe' './recognize_chars.py' --library './character_library/library_custom.npz' --chars-dir './integration/B_original/output/blue_7_chars'
```

默认构库命令会更新默认 `library.npz`；建议先另存 custom，确认后再替换。
重复归一化图会去重；同图不同标签、坏图片、未知目录名会报错，须先修正再构库。
不要把 validation/test 或待评分图片加回训练目录，也不要把 B 的六张测试切片直接加入训练。
新增自有训练图片不会自动写入原始来源清单，需自行补记录并重新划分独立评估集。

随包有两个库：默认库 9517 张 = 公开训练 9130 张 + 字体辅助 387 张；
`library_real_only.npz` 是仅公开训练样本的对照库。字体模板已经生成，运行时不需要本机安装同样字体。

## 8. 复现评估和自动检查

```powershell
& 'D:/应用/python.exe' './evaluate_chars.py' --split validation
& 'D:/应用/python.exe' './evaluate_chars.py' --split test
& 'D:/应用/python.exe' -m unittest discover -s tests -v
```

评估输出位于 `results/validation` 和 `results/test`，会更新同名文件；需要保留旧结果时加 `--output './results/local_test'`。
结果包括逐图预测、每类召回率、混淆矩阵、Top3 和失败图。默认库测试 Top1 为 97.45%，
Top3 为 99.03%。此处是同源独立字符集，不是整牌端到端指标。
`compare_features.py` 只用 validation 和 real-only 库复现五个权重比较。
`prepare_data.py`、`generate_font_samples.py` 是首次数据准备工具，交付已包含其输出，日常不用再运行。
生成 PDF 另需 ReportLab，运行识别并不需要它。

## 9. 常见问题

| 现象 | 处理 |
|---|---|
| `ModuleNotFoundError: cv2` | 用同一个 Python 安装 requirements，不要混用 Conda 与系统解释器 |
| `invalid_length` | B 切片数非 7/8，先检查倾斜、粘连、漏字；不要补假字符 |
| `partial_failure`、某字为 `?` | 该字符空白、坏图或范围不对；位置保留，修好切片再试 |
| `needs_review` | 查看 Top3、原始切片和 margin，保留人工复核提示 |
| Windows 中文路径读图失败 | 使用本模块 read_image，或传 NumPy 数组；不要改成普通 cv2.imread |
| 切片颜色是 RGB | 灰度切片直接用；彩色传 C 前转 BGR，见接口说明 |
| 库版本不符 | 用当前 build_library.py 重建，不能混用旧特征实现的库 |
| 不识别学/警/港等 | 当前 65 类没有这些字符，需扩充标签、样本和规则后重新验证 |

CLI 退出码：0 = 成功或建议复核；2 = 空切片/长度错误/部分字符无效；1 = 配置或资源错误。
复核提示不是已确定错误，`ok` 也不保证一定正确；相似度不是正确概率。

## 10. 验证环境与依赖变更

本次实际运行：Windows 11，Python 3.13.7，NumPy 2.3.5，
OpenCV 5.0.0（发行包 opencv-python 5.0.0.93），Pillow 12.0.0。
PDF 生成使用已有 ReportLab 5.0.1。全部复用 `D:/应用` 环境，没有安装新包或改动全局配置。
requirements.txt 写的是兼容范围，其他版本组合未逐一实测。17 项行为检查及 ZIP 解压验收记录见交付说明。
