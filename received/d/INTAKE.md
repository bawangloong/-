# 角色 E 收下的 D 模块

来源是同一发布页的 `plate_D_full_with_exe.zip`（页面标签 `车牌识别系统_D部分_完整版含exe.zip`）。SHA-256：`d4bd98ba8a778d61cd04db58d0979eb255da94447a709bf1de5b1f76b6fc9d81`。顶层目录 `车牌识别系统/` 已展开到这里，业务代码没有改。

发布包里还有完整的 Windows 运行时 `runtime/`，解压后约 209 MB。其中 `runtime/Lib/site-packages/cv2/cv2.pyd` 单文件 112.9 MB，超过 GitHub 单文件 100 MB 的限制，所以 `runtime/` 没有放进这个仓库。可运行的完整包仍以发布页上的 zip 为准。这里的 `车牌识别系统.exe` 只有约 4.6 KB，是启动器，旁边没有 `runtime/` 时不能单独打开。

源码依赖见 `requirements.txt`：NumPy 2.3.5、`opencv-contrib-python==5.0.0.93`、Pillow 12.0.0。README 写的 `python main.py` 在包里没有这个文件。实际入口是：

```bash
python app_main.py          # 绿色包入口，会打开 GUI
python -m app.main          # GUI
python -m app.cli samples/normal_blue.png
python -m app.cli samples/multi_two.png --json
```

这些命令要在 `received/d/` 下执行，并且本机已安装上面的依赖。当前仓库没有在根目录放 `pipeline.py`。

## 实际接口

统一入口是 `app/pipeline.py` 里的 `PlatePipeline`，不是仓库根目录的 `run(image_path)`。

```python
from app.pipeline import PlatePipeline, result_to_json

pipeline = PlatePipeline()                 # 启动时加载 vendor/c_char/character_library/library.npz
result = pipeline.recognize_file("某图.png")
payload = result_to_json(result)           # 去掉 numpy 图像后再写 JSON
```

`recognize_file` 先读成 BGR。没有车牌时 `plates` 为空，`ok` 为 false，`error.code` 为 `no_plate`。有牌时每块包括：

- `bbox`：原图上的 `[x, y, w, h]`
- `quad`：四个角点，可能为空
- `text`：整牌字符串
- `color`：B 的字典，英文类在 `color["color"]`，中文在 `color["label"]`
- `segmentation.count` 和 `segmentation.status`：`ok` / `count_abnormal` / `no_char`
- `recognition`：C 的逐字结果，含 `similarity`
- `chars`：字符图，只留在内存里，`result_to_json` 会去掉

流水线顺序是检测、矫正、颜色、分割、识别。检测优先用 `vendor/a_plate/`；这个目录目前没有 A 的代码，所以走 `app/detector.py` 里的内置检测。`vendor/b_plate/` 和 `vendor/c_char/` 是 D 随包放的 B、C 副本。D 的 README 写明 B 增加了可选参数 `min_char_width_ratio`，C 改了相对导入。E 没有再改这些文件。

提交仓库 https://github.com/bawangloong/plate-recognition-submit 的 main 上，根目录 `pipeline.run(image_path)` 会调用这里的 `PlatePipeline`，再用 `result_to_json` 去掉图像数组。本仓库根目录还没有那个文件，所以直接跑 `python eval/evaluate.py` 仍会报 `pipeline missing`。字段对应关系写在 `eval/README.md`：`bbox` 收成 `box`，`color.color` 收成颜色字符串，`segmentation.count` 收成 `char_count`，`text` 收成 `number`。

## 和课程测试表的关系

README 里的演示表是 D 用 `samples/` 合成图写的流程记录。E 没有在这台机器上复跑 GUI 或命令行，那些耗时和号码不是课程测试表。
