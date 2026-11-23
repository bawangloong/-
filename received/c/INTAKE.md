# 角色 E 收下的 C 模块

来源是同一发布页的 `plate_char_C_1.zip`（页面标签 `plate_char_C(1).zip`）。SHA-256：`269bfb7e46b6377ccaf9b971ce6d4684e13da50d591effb6fde766c6a68f314d`。顶层目录 `plate_char_C/` 已展开到这里，代码没有改。

它不检测整张街景。输入是已经按从左到右排好的字符图，或者一块已经摆正的车牌再交给包内未改过的 B。

在 `received/c/` 里运行。依赖见 `requirements.txt`：NumPy、OpenCV、Pillow。使用说明里的 Python 路径是提交者自己的电脑，换机器后改成当前解释器。

```bash
python recognize_chars.py --chars-dir integration/B_original/output/blue_7_chars --output results/local_blue.json
python recognize_chars.py --image integration/B_original/output/blue_7_chars/char_01.png --charset province
python integration_example.py
python integration_example.py --image 已矫正车牌.png --output results/local_real_plate
python build_library.py --output character_library/library_custom.npz
```

`integration_example.py` 会调用 `integration/B_original` 里的 B，再做识别。倾斜样例若只切出 5 个字符，状态是 `invalid_length`，号码留空。

## 实际接口

```python
from recognize_chars import CharacterRecognizer

recognizer = CharacterRecognizer()  # 默认读旁边的 character_library/library.npz
result = recognizer.recognize_chars(char_images, layout="standard", top_k=3)
one = recognizer.recognize_char(image, allowed_labels=None, top_k=3)
```

`char_images` 按阅读顺序，不含间隔圆点。B 的 40×20 白字黑底灰度图可以直接传。彩色数组按 BGR。`layout="standard"` 用于 7 或 8 个字符；其它长度用 `"unrestricted"`，否则状态会是 `invalid_length`，`text` 为空。

返回字段：`text` 整牌字符串，`character_count`，`status`，`characters`。每个字符有 `label`、`similarity`、`margin`、`candidates`。`status` 可以是 `ok`、`needs_review`、`no_characters`、`invalid_length`、`partial_failure`。相似度是特征余弦，不是正确率。

构库入口是 `build_library.py`。默认库文件是 `character_library/library.npz`，旁边的 `library.json` 是索引。`library_real_only.npz` 是他们留的对照库。训练图在 `character_library/train/<标签>/`。他们的说明要求不要把 validation、test 或 B 的六张演示切片放进训练目录。

类别是 65 个：数字、去掉 I 和 O 的大写字母、31 个省份简称。没有学、警、使、领、港、澳、挂。

## 和课程测试表的关系

`results/` 和使用说明里有他们自己的字符集评估和六张合成牌联调记录。E 没有复跑，这些数字不是课程的整牌测试表，也没有写入 `data/splits/manifest.json`。
