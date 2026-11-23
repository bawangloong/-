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
