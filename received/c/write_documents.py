"""根据已经生成的评估 JSON 写出准确的中文交付说明（不运行识别实验）。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def percent(value):
    return f"{value * 100:.2f}%"


def write(name, content):
    (ROOT / name).write_text(content.strip() + "\n", encoding="utf-8")


def main():
    data = read("data_summary.json")
    fonts = read("font_samples_summary.json")
    model = read("character_library/library.json")
    test = read("results/test/metrics.json")
    val = read("results/validation/metrics.json")
    b = read("results/B_integration/summary.json")
    baseline = read("results/baseline_hog_test/metrics.json")
    real = read("results/real_library_test/metrics.json")
    final = test["unrestricted"]["all"]
    constrained = test["type_constrained"]["all"]
    write("README_使用说明.md", f'''
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

随包有两个库：默认库 {model['samples']} 张 = 公开训练 {data['split_counts']['train']} 张 + 字体辅助 {fonts['count']} 张；
`library_real_only.npz` 是仅公开训练样本的对照库。字体模板已经生成，运行时不需要本机安装同样字体。

## 8. 复现评估和自动检查

```powershell
& 'D:/应用/python.exe' './evaluate_chars.py' --split validation
& 'D:/应用/python.exe' './evaluate_chars.py' --split test
& 'D:/应用/python.exe' -m unittest discover -s tests -v
```

评估输出位于 `results/validation` 和 `results/test`，会更新同名文件；需要保留旧结果时加 `--output './results/local_test'`。
结果包括逐图预测、每类召回率、混淆矩阵、Top3 和失败图。默认库测试 Top1 为 {percent(final['top1_accuracy'])}，
Top3 为 {percent(final['top3_accuracy'])}。此处是同源独立字符集，不是整牌端到端指标。
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

本次实际运行：Windows 11，Python {test['environment']['python']}，NumPy {test['environment']['numpy']}，
OpenCV {test['environment']['opencv']}（发行包 opencv-python 5.0.0.93），Pillow {test['environment']['pillow']}。
PDF 生成使用已有 ReportLab 5.0.1。全部复用 `D:/应用` 环境，没有安装新包或改动全局配置。
requirements.txt 写的是兼容范围，其他版本组合未逐一实测。17 项行为检查及 ZIP 解压验收记录见交付说明。
''')
    write("方法讲解.md", '''
# C 部分方法讲解

## 1. 先理解整体思路

B 已经把号码拆成一张张小图，C 不再寻找车牌或切字。C 要回答的是：“这张小图最像哪个已知字符？”
因此每类保留多个样本，把输入与全部样本比较，选择最像的类别，再按原顺序拼回号码。
一个“京”可能模糊、倾斜、断笔，所以每类有多个模板，比每类只用一张标准字更有代表性。

```text
有序字符 -> 统一前景/尺寸 -> HOG + 像素特征 -> 与样本库计算相似度
        -> 每类取最佳样本 -> 不同类别 Top3 -> 位置约束/复核 -> 拼接文字
```

## 2. 预处理为什么要统一

1. 灰度化后用 Otsu 自动选阈值，使图像成为前景和背景两类。
2. 查看四周边界像素的多数颜色，以此判断背景。必要时反色，统一为白字黑底。
3. 找全部前景的包围框，裁掉多余背景。汉字可能有分离笔画，不能只保留最大连通域。
4. 保持长宽比，将最长边缩放到 28 像素，居中放到 32×32 画布；缩放使用面积插值。

这使原来 40×20 的 B 切片与来源不同的训练图能在同一坐标系下比较。
纯色、前景不足、非有限值等输入返回 invalid_input；未做复杂去污、透视矫正或自动补字。
边界投票假定字符已基本切好；若边框/污点很大，仍可能误判前景或裁剪范围。

## 3. HOG 表示笔画的方向

对灰度值 f(x,y)，用中心差分近似梯度：

```text
gx = f(x+1,y) - f(x-1,y)
gy = f(x,y+1) - f(x,y-1)
magnitude = sqrt(gx^2 + gy^2)
orientation = atan2(gy,gx) mod pi
```

梯度指向亮度变化最快的方向。数字 1 以竖边为主，A 有斜边和横边，因此方向统计能描述结构。
无符号方向只区分 0-180 度，把相反方向的同一条边视为相同。

本实现将 32×32 分为 4×4 个 8×8 cell；每个 cell 有 9 个方向 bin。
像素按梯度幅值投票，并向相邻两个方向 bin 线性分票，不做 cell 之间的空间插值。
每个 2×2 cell 组成一个 block，步长一个 cell，共 3×3 block：

```text
HOG 维数 = 3×3 blocks × 2×2 cells × 9 bins = 324
```

每个 block 做 L2 归一化、将分量截断到 0.2、再 L2 归一化，即 L2-Hys。
拼接后再做 L1、逐元素平方根、L2 归一化，获得单位向量 h。
平方根变换可减弱少数强梯度的支配作用。这是明确参数的 NumPy HOG 实现，不是直接调用 OpenCV HOGDescriptor。

## 4. 为什么再加入像素轮廓

只统计方向会忽略精确位置，京/黑等汉字仍可能方向相似。归一化已对齐的情况下，
原图像素能补充笔画位置。把 32×32 灰度图展平为 1024 维并做 L2 归一化，得到单位向量 p。

```text
z = concat(sqrt(0.55) * h, sqrt(0.45) * p)
特征维数 = 324 + 1024 = 1348
```

由于 h 和 p 长度均为 1，z 的长度也为 1。查询 q 与样本 s 的点积恰好等于：

```text
S(q,s) = zq dot zs
       = 0.55 * cosine(hq,hs) + 0.45 * cosine(pq,ps)
```

像素权重通过 validation 中 0、0.15、0.30、0.45、0.60 五个候选选择。
0.45 的总体 Top1 最好，固定后用于后续评估，没有根据每张输入或期望号码临时切换参数。

## 5. 怎样从样本变成答案

假设标签为 c 的样本集合是 Lc，对每个类别取最相似样本：

```text
score(c) = max(S(query, sample) for sample in Lc)
answer = argmax_c score(c)
```

这是最近样本分类：在单位向量上，最大余弦也等价于最小欧氏距离，因为
`||q-s||^2 = 2 - 2(q dot s)`。测试中用 float64 欧氏距离独立核对了排序。
Top3 表示三个不同类别；不会把同一个字符的三张图当成三个候选。
同时返回最佳样本路径和库中索引，GUI 可直接显示“匹配到了哪张样本”。

## 6. 位置约束与异常

standard 模式：第一位只选省份汉字，第二位只选字母，后续选数字/字母；仅接受 7 或 8 张切片。
unrestricted 模式：不限制类别或长度，适合单字符实验和诊断。
这里只覆盖常见民用结构，不完整校验新能源 D/F 位置、军警、使馆、港澳等全部号牌规则。

设不同类别的前两名分数为 s1、s2，margin=s1-s2。
默认 s1<0.75 或 margin<0.02 时标记 needs_review；这是启发式阈值，不是经过概率校准的置信度。
坏字符输出 ? 并保持位置；长度错误返回 invalid_length，避免漏一个字后把后续位置全部错移。

## 7. 字体模板与结果边界

公开车牌字符数据和 B 的屏幕字体外观不同。补充模板对全部 65 类统一生成：
微软雅黑/黑体，48/64/80 字号，独立渲染，再按 40×20 切片约定缩放。
未读取 B 的图片、切片或号码答案来构造模板；也没有复制 B 切片进训练集。
字体二进制没有随包分发，日常识别无需本机字体。

B 的合成图使用了相同字体家族，因此这是接口及同字体兼容验证，不能称为跨字体或真实道路泛化。
最终独立字符集仍然来自同一公开来源；去重排除了归一化像素完全相同的图，不能排除近重复或原始同车牌。
汉字稀有类别样本少，藏只有 4 张公开训练样本、1 张测试样本，单类百分比不稳定。
后续最有价值的工作是让 A/B 提供新的真实图与标注，针对字体差异、断笔、粘连补充训练样本，再做独立整牌评估。

## 8. 口头讲解参考

“我负责字符样本库和字符识别。B 输出从左到右的 40×20 灰度切片，我先统一前景、裁边并等比例缩放到 32×32。
然后提取 324 维 HOG 和 1024 维像素特征，按验证集选出的 0.55/0.45 权重拼接。
查询与库中样本做余弦匹配，每个类别保留最相似样本，输出不同类别 Top3，再加常见位置约束。
分数低或候选接近时提示复核，坏切片保留问号，数量异常交回上游检查。
我分别测试了独立字符集和 B 的合成样例，两个指标代表的范围不同，完整系统仍需真实整牌测试。”
''')
    write("接口说明_B_D.md", '''
# 给 B、D 的接口说明

## 1. 最小对接：直接接 B 的返回值

把 C 核心 .py 与 `character_library/library.npz` 放在可导入的目录。只初始化一次：

```python
from recognize_chars import CharacterRecognizer
from integration_example import recognize_b_result

recognizer = CharacterRecognizer()  # 初始化时加载库；后续复用
# b_result = segment_plate(plate_rgb, ...)
c_result = recognize_b_result(b_result, recognizer)
text = c_result["text"]
rows = c_result["characters"]
status = c_result["status"]
```

`recognize_b_result` 校验 B 的 count 和 chars 长度是否一致，并传递 B 的分割状态。
如 D 不需要适配器，也可直接 `recognizer.recognize_chars(b_result['chars'])`，
但必须自己展示 B 的异常状态。颜色由 B 输出，C 不重复判断颜色。

## 2. 完整 B -> C 示例

```python
import numpy as np
from PIL import Image
from integration_example import BToC

pipeline = BToC()  # 默认使用 integration/B_original 中未改动的 B 模块
plate_rgb = np.asarray(Image.open("rectified_plate.png").convert("RGB"))
result, b_result = pipeline.run(plate_rgb)
print(result["color"]["label"])
print(result["segmentation"]["count"])
print(result["recognition"]["text"])
# b_result['chars'] 可作为 GUI 字符预览
```

BToC 输入是 **RGB uint8**；若 A 用 cv2 产生 BGR，可传 `plate_bgr[:, :, ::-1].copy()`。
B 的 segment_plate 文档对 boxes 坐标有冲突；核对代码后，实际是高度归一化到 140 的 norm 图坐标，
不能直接在 A 的原尺寸图上画框。若要回原图，应按 norm/原图宽高缩放，或由 B 修正接口文档。

## 3. C 核心输入

```python
recognizer.recognize_char(image, allowed_labels=None, top_k=3)
recognizer.recognize_chars(characters, layout="standard", top_k=3)
```

- characters：list/tuple，按阅读顺序，不含中间圆点；默认 7/8 张。
- image：NumPy 数组或图片路径，支持中文路径。
- 允许灰度 H×W、H×W×1、BGR H×W×3、BGRA H×W×4；透明背景会合成白色。
- 数据为 uint8 0-255、bool、uint8 0/1，或有限 [0,1] 浮点；其他整数范围请先转换。
- B 实际给出的 40×20 白字黑底灰度图可直接传。彩色图给 C 时按 BGR；BToC 的彩色入口则按 RGB。
- C 内部裁边后再次归一化，不要求上游也缩放成 32×32。
- position 从 0 开始；对用户展示时可加 1。

## 4. 输出结构

```json
{
  "text": "京A12345",
  "character_count": 7,
  "layout": "standard",
  "status": "ok",
  "warnings": ["位置约束仅覆盖常见民用 7/8 位结构，不验证全部号牌规则"],
  "score_definition": "... not a correctness probability",
  "characters": [
    {
      "position": 0,
      "label": "京",
      "similarity": 0.96,
      "margin": 0.08,
      "status": "ok",
      "message": "",
      "candidates": [
        {"label": "京", "similarity": 0.96, "sample_index": 123, "sample_path": "zh_jing/example.png"}
      ]
    }
  ]
}
```

上面数值、索引、路径是字段示意，实际结果见 results/B_integration/*.json。
相似度为组合特征的余弦，等价于 0.55×HOG余弦 + 0.45×像素余弦，范围近似 [0,1]。
只有一个候选类别时 margin 为 null，纯色等无效字的相似度也为 null。
GUI 不要将相似度乘 100 后标成“正确率”。

| status | D 如何处理 |
|---|---|
| ok | 展示识别号码和可选的候选详情 |
| needs_review | 展示号码并提示人工复核，保留 Top3 |
| no_characters | 提示未分出字符 |
| invalid_length | 提示切片非 7/8 张，text 为空；回看分割/矫正 |
| partial_failure | 显示含 ? 的号码，对应坏切片位置高亮 |
| 单字符 invalid_input | 显示具体 message，不丢掉该位置 |

配置错误、未知 layout、top_k 非正整数、坏库等抛 ValueError/OSError，GUI 应捕获并提示资源或配置错误。
`rank_features()` 是批量评估入口，GUI 日常无需自己构造特征。

## 5. 显示匹配到的样本

```python
candidate = rows[0]["candidates"][0]
template_32 = recognizer.normalized_images[candidate["sample_index"]]  # uint8，白字黑底
original_file = recognizer.library_path.parent / "train" / candidate["sample_path"]
```

归一化图已包含在 npz 中，GUI 显示候选不要求保留全部原图；要显示原始样本才需要训练目录。
候选 sample_index 只对当前加载库有效，重新构库后可能改变。

## 6. 集成和打包给 D

最小推理文件：`labels.py`、`char_features.py`、`build_library.py`（识别模块引用其中图片扩展名常量）、
`recognize_chars.py`、`character_library/library.npz`。需要图示再带 `visualize_matches.py` 和 Pillow。
直接按 B 结果调用时还带 `integration_example.py`；B 原文件可使用团队统一目录。
npz 大约 10 MB，初始化后占用更多内存，避免每帧或每字重新加载。
识别对象的特征数组只读，不修改输入图。GUI 放工作线程执行，避免界面阻塞。

PyInstaller 建议显式把资源加入包（版本支持时用 `--add-data "character_library/library.npz:character_library"`），
或者由 D 解析运行时资源路径后传给 `CharacterRecognizer(actual_npz_path)`。
默认路径以 recognize_chars.py 的位置为基准，不依赖工作目录；仍需在最终 exe 中验证资源实际位置。
C 没有生成完整系统 exe，也没有在无 Python 电脑上验收；这是 D/E 后续的系统交付检查。

## 7. 不应忽略的边界

不支持“学、警、使、领、港、澳、挂”等额外字符，也未实现全部特殊车牌布局。
字符数正确并不代表切片正确，强反光、粘连或断笔可能造成高分误识别。
B 的示例是合成字体，正式联调应增加 A 提供的不同场景真实车牌，并保留逐字真值。
B 原 README 中“已与 C 商量好”等措辞是原包内容；本次以实际代码与像素一致性检查确认接口兼容。
''')
    metrics_table = "\n".join(
        f"| {title} | {test['unrestricted'][group]['count']} | {percent(test['unrestricted'][group]['top1_accuracy'])} | {percent(test['unrestricted'][group]['top3_accuracy'])} |"
        for title, group in [("全部", "all"), ("数字", "digits"), ("字母", "letters"), ("省份汉字", "provinces")])
    b_table = "\n".join(f"| {r['file']} | {r['truth']} | {r['count']} | {r['prediction'] or '不输出号码'} | {r['status']} |" for r in b['rows'])
    write("C部分报告.md", f'''
# 车牌识别系统 C 部分：字符库与匹配识别

## 一、任务和实现范围

本模块接收 B 输出的从左到右字符切片，完成字符特征提取、样本库匹配、逐字候选输出与号码拼接。
提供独立命令行、Python 接口、样本库构建程序、匹配过程可视化、独立字符评估和 B 联调示例。
检测定位与矫正属于 A，颜色和切字属于 B，GUI、exe 与系统集成属于 D，整体验收及报告整合属于 E。

## 二、数据和来源

数据来自 [License-Plate-Recognition](https://github.com/wzh191920/License-Plate-Recognition)，固定提交
`{data['commit']}` 中 chars2.7z、charsChinese.7z。上游说明数据来源于 EasyPR。
保留下载地址、文件大小、git blob SHA1、SHA256、源 README、MIT 及 EasyPR Apache 许可证。
原始支持类别图片 {data['raw_supported_images']} 张；归一化像素 SHA256 去重 {data['excluded_counts']['duplicate_normalized_pixels']} 张，
跨标签冲突排除 {data['excluded_counts']['conflicting_labels']} 张，保留 {data['kept_images']} 张。
invalid 为 {data['invalid_count']}。排除明细在 third_party/excluded_samples.json。

采用随机种子 {data['seed']}，按类别约 70%/15%/15% 划分，训练 {data['split_counts']['train']}、
验证 {data['split_counts']['validation']}、测试 {data['split_counts']['test']} 张；归一化去重在划分之前完成。
共 65 类，类别不均衡；藏仅 6 张独立图，其中公开训练 4、验证 1、测试 1。
上游 zh_qing 使用异体“靑”，本实现统一输出规范字“青”。
为适配屏幕字体输入，额外独立渲染全部 65 类的辅助模板 {fonts['count']} 张，
字体为微软雅黑/黑体、字号 48/64/80。未用 B 切片作训练，字体二进制不随包分发。
最终训练库共 {model['samples']} 张。字体与公开评估图片没有归一化哈希交集。

![字符库](results/library_65_classes.png)

## 三、算法

Otsu 二值化，按边界判断背景并统一极性，裁前景框，等比例缩放并居中放入 32×32。
保留所有汉字笔画，不只取最大连通域。提取 NumPy 实现的 324 维 Root-HOG，以及 1024 维单位像素向量。
两者以 sqrt(0.55)、sqrt(0.45) 缩放后拼接，得到 1348 维单位向量。
查询与样本的点积等价于 0.55×HOG 余弦 + 0.45×像素余弦；每类取最佳样本，再选择不同类别 Top3。

standard 模式首位限省份、第二位限字母、后续限数字/字母，接受 7/8 位；不是完整号牌规则校验。
默认相似度低于 0.75 或前两类差值小于 0.02 时建议复核，阈值是启发式，分数不是正确概率。
坏切片保留 ?，数量异常返回空号码及状态，避免静默补字。

## 四、验证集选择与对照

在公开训练库上，仅用 validation 比较像素权重 0/0.15/0.30/0.45/0.60，
Top1 依次为 91.73%/95.61%/96.78%/96.88%/96.53%，取 0.45。
之后因 B 合成字体失配，新增对全部类别统一生成的字体模板；保留补充前后结果。
最终 validation Top1 为 {percent(val['unrestricted']['all']['top1_accuracy'])}。
最初 HOG 基线测试结果曾被查看，后续选择权重使用 validation；因此这是开发留出集结果，
不是一次性盲测。正式结论还需新增未参与开发的真实外部数据。

| 方案 | 留出测试 Top1 | 结果目录 |
|---|---|---|
| 仅 Root-HOG，公开训练库 | {percent(baseline['unrestricted']['all']['top1_accuracy'])} | results/baseline_hog_test |
| HOG+像素，公开训练库 | {percent(real['unrestricted']['all']['top1_accuracy'])} | results/real_library_test |
| HOG+像素，公开训练+字体模板 | {percent(final['top1_accuracy'])} | results/test |

compare_features.py 可复现权重比较。基线和中间失败结果均保留，未只保留最好的输出。

## 五、最终单字符测试

| 类别 | 数量 | 无类别约束 Top1 | 无类别约束 Top3 |
|---|---:|---:|---:|
{metrics_table}

Top1 共 {final['top1_correct']}/{final['count']}，宏平均类别召回率 {percent(final['macro_recall'])}。
知道首位为省份、其余为字母数字的类型约束下，Top1 为 {percent(constrained['top1_accuracy'])}，
Top3 为 {percent(constrained['top3_accuracy'])}；此实验没有额外使用“第二位只限字母”的更强约束。
无约束结果中 {final['review_count']} 张建议复核，自动接受 {final['auto_accepted_count']} 张中仍有
{final['auto_accepted_count'] - round(final['auto_accepted_count'] * final['auto_accepted_accuracy'])} 张错误，说明 ok 不是正确性保证。
批量 128 测试时，含读图/预处理的平均单字耗时约
{test['timing']['mean_extract_and_batch_match_ms_per_char']:.2f} ms，属于本机批量测量，不能视为 GUI 单字延迟承诺。
逐图结果、每类召回和完整混淆矩阵分别见 predictions.csv、per_class.csv、confusion_matrix.csv。

## 六、B -> C 实际联调

B 原始代码与样例原样保存在 integration/B_original。重新运行颜色与切字后，
六组切片与原包存档逐像素一致。B 输出为 40×20 灰度白字黑底，可直接进入 C。

| 样例 | 真值 | 切片数 | 输出 | C 状态 |
|---|---|---:|---|---|
{b_table}

六张中五张完整识别，五张分割正常图全部完整匹配；倾斜图只切出 5 字，拒绝拼成常规车牌。
未补字体模板时只有 1/6 完全正确，旧结果保存在 results/real_library_B_integration，说明字体覆盖的重要性。
这些图和辅助模板使用同字体家族，因此只能证明该合成输入与接口兼容，不能证明真实整牌泛化。

![B 联调示例](results/B_integration/blue_7_matches.png)

## 七、失败案例与局限

![测试错误样本](results/test/failure_cases.png)

同形字符 D/0、7/T、B/M 与低分辨率汉字仍会混淆；部分公开样本本身有噪点、断笔或裁切损失。
Top3 展示了其他候选，人工复核可参考原始切片与最佳模板，但不能仅靠分数判真伪。
同源随机划分只排除了完全相同的归一化图，仍可能存在近重复和共同原始车牌。
稀有类数量少、特殊字符未支持、上游切割错误及严重透视反光等仍需后续解决。
当前没有 A 的新真实图、完整 GUI、exe 和无 Python 机器验收，不能声称完成整个小组系统。

## 八、可复现性与贡献

环境：Python {test['environment']['python']}、OpenCV {test['environment']['opencv']}、NumPy {test['environment']['numpy']}、
Pillow {test['environment']['pillow']}，CPU 运行。17 项行为检查通过，包含中文路径、极性、输入格式、
坏字符位置、7/8 位、Top3 类别去重、独立距离核验、全量哈希与划分隔离、构库冲突检测、B 像素复现及 CLI 退出码。
ZIP 解压后的离线识别、重新构库和结果一致性验收见 acceptance_record.json。
C 的工作为样本来源与去重、特征实现、样本库、匹配接口、异常/复核、可视化、评估与文档。
没有新增系统依赖，requirements.txt 记录运行所需三项包；PDF 工具复用已有 ReportLab。

## 九、来源

- [公开字符集及源代码仓库](https://github.com/wzh191920/License-Plate-Recognition/tree/{data['commit']})
- [EasyPR](https://github.com/liuruoze/EasyPR/tree/c32d69c50439f02b3ab9b4230048b2895d876d16)
- 用户提供 B模块_颜色识别与字符分割.zip；SHA256：991805eaa12565ef4f9875b5a7b336128b1e8ad7f9c77b40501cce825957482f。
- 算法与评估说明对应当前代码，字体模板为本次独立生成，未宣称公开原始样本由本组采集。
''')
    write("交付清单.md", f'''
# C 部分交付清单

## 交给 D：直接集成的程序

- [x] recognize_chars.py：单字符/整牌接口和 CLI。
- [x] char_features.py、labels.py：共用预处理、手写 NumPy HOG、组合特征和 65 类映射。
- [x] build_library.py：构库和冲突检测。
- [x] character_library/library.npz、library.json：{model['samples']} 张模板，1348 维，含归一化预览图。
- [x] integration_example.py：B -> C 可运行适配，输入 RGB，输出颜色/分割/识别。
- [x] visualize_matches.py：Top3 匹配过程图。
- [x] requirements.txt、接口说明_B_D.md：依赖与准确的字段、错误状态、打包资源说明。

## 交给 B：联调证据

- [x] integration/B_original：原始代码、合成输入、原始切片及文档，内容未修改。
- [x] results/B_integration：六张图重新运行的切片、JSON、匹配图和汇总。
- [x] 五张正常合成车牌全部识别；倾斜图保持 invalid_length。
- [x] 确认 40×20 灰度切片兼容；指出 boxes 实际是 norm 图坐标。

## 交给 E：报告、评估和可复现材料

- [x] C部分报告.md：可并入总报告的实现、实验、结果边界和失败分析。
- [x] C部分说明与报告.pdf：全黑文字的阅读版，涵盖使用、接口、方法和实验。
- [x] results/test、results/validation：指标 JSON、逐图 CSV、混淆矩阵、失败案例。
- [x] results/baseline_hog_*、results/real_library_*：对照与开发失败结果。
- [x] data_manifest.csv、data_summary.json：来源、种子、划分和哈希。
- [x] font_samples_manifest.csv、font_samples_summary.json：辅助模板完整来源记录。
- [x] third_party：来源 README、许可证、排除样本记录和来源说明。
- [x] tests/test_c_module.py、results/test_checks.log：17 项行为检查。
- [x] acceptance_record.json：ZIP 解压验收证据；最终以实际记录为准。

## 留给自己：理解与演示

- [x] README_使用说明.md：当前机器、换机、运行、构库、评估和常见错误。
- [x] 方法讲解.md：直觉、公式、1348 维来源、逐类最大匹配和口头讲解。
- [x] character_library/train：公开训练 {data['split_counts']['train']} 张与字体 {fonts['count']} 张。
- [x] character_library/library_real_only.npz：只用公开训练集的组合特征对照库。
- [x] evaluation_data：独立验证 {data['split_counts']['validation']}、测试 {data['split_counts']['test']} 张。
- [x] prepare_data.py、generate_font_samples.py、compare_features.py：数据准备和参数选择复现。

## 当前尚未覆盖的系统工作

这些不属于本次 C 交付的已验证结论：A 的真实图检测/矫正、未见场景真实整牌准确率、完整 GUI、
最终 exe、在无 Python 电脑上的部署、小组总报告/五分钟视频。需 A、D、E 继续集成。
普通字体模板提高合成样例兼容性，不能替代真实数据验证；特殊字符和特殊号牌规则也未包含。

本次没有安装新依赖或修改 B 源码；有三个运行依赖文件条目，复用已有解释器环境。
''')
    write("third_party/来源说明.md", f'''
# 数据及外部材料说明

## 公开字符样本

来源 https://github.com/wzh191920/License-Plate-Recognition ，固定提交 {data['commit']}。
原始两个压缩包的大小、URL、git blob SHA1、SHA256 见 data_summary.json。
保留该仓库 MIT LICENSE 和 README。上游说明训练数据来自 EasyPR，
同时保留 EasyPR 固定提交 c32d69c50439f02b3ab9b4230048b2895d876d16 的 Apache LICENSE。
这些是上游公开声明及来源记录，不表示本组拥有或重新授予所有原始图像权利。
仅用于本次课程实现和可复现验证；对外再次分发或商用时应另核查原始数据权利。

## 字体辅助图片

在当前 Windows 上用 msyh.ttc、simhei.ttf 独立渲染全部 65 类字符，得到 {fonts['count']} 张去重图片。
未分发字体文件。图片只用于课程模板实验，不声称字体属于本组或可无限制商用。
font_samples_manifest.csv 记录每张图片的字体、字号、标签和哈希。

## B 原始交付

用户直接提供 B模块_颜色识别与字符分割.zip，原包 SHA256：
991805eaa12565ef4f9875b5a7b336128b1e8ad7f9c77b40501cce825957482f。
内容原样解压至 integration/B_original；其中 samples 是合成图，output 是 B 的原始结果。
本次仅作为组内接口输入复用，没有把 B 输出切片作为训练模板。

## 开发记录

首次下载发生 SSL EOF，增加有限重试后成功；未关闭 TLS 证书校验。
本机 OpenCV 不提供 HOGDescriptor，因此采用明确参数的 NumPy HOG，
仍使用 cv2 的读图、灰度、Otsu 和 resize；运行没有要求额外安装 objdetect 或神经网络。
保留 HOG 基线与组合特征/字体补充前后的结果，避免只报告最佳运行。
''')
    from recognize_chars import CharacterRecognizer
    from visualize_matches import save_library_sheet
    save_library_sheet(CharacterRecognizer(), ROOT / "results/library_65_classes.png")
    print("中文使用说明、方法、接口、报告及交付清单已更新")


if __name__ == "__main__":
    main()
