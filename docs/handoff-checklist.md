# 角色 E 交接清单

仓库里现在有数据约定、评测入口、这份清单，以及 A、B、C、D 交来的代码，分别在 `received/a/`、`received/b/`、`received/c/`、`received/d/`。课程测试表、报告、幻灯片和讲解稿在 `eval/results/` 与 `docs/course/`。视频文件和完整小组 ZIP 还没有。各组自己文档里的数字不要抄进课程测试表。

作业要求来自课程大作业：检测是否有车牌、定位并给出车牌图、分割后与字符库匹配、输出颜色和字符数及识别结果，并准备 GUI、exe、报告、视频和一份小组 ZIP。视频要讲原理、运行逻辑、实际演示和异常处理，时长不超过 5 分钟。报告要写小组分工。

## 已经有的

- 四个划分里的图像、JSONL 标注和清单。每条 `source` 写了来源。
- `data/check_dataset.py`：字段、划分泄漏、完全重复和近似重复。
- `eval/evaluate.py`：流水线不在时明确退出；合成夹具只验证指标算术。
- 指标口径：`eval/README.md`。
- A 的检测和矫正：`received/a/`。说明见 `received/a/INTAKE.md`。
- B 的颜色识别和字符分割：`received/b/`。说明见 `received/b/INTAKE.md`。
- C 的字符库和识别：`received/c/`。说明见 `received/c/INTAKE.md`。
- D 的界面和流水线：`received/d/`。说明见 `received/d/INTAKE.md`。Windows 运行时因为单文件超过 GitHub 限制，没有放进仓库。

## 测试表之前

测试表指 validation / final_test 上的定位、颜色、字数、逐字、整牌和耗时。正式清单已经填好。冻结的那一次运行在 `eval/results/system-evaluation.json`。

角色 A：代码已经在 `received/a/`。评测接入时还要遵守这些点：

- `detect_plates(bgr)` 返回 `PlateRegion` 列表，没有车牌时是空列表。`bbox` 是原图 `(x, y, w, h)`。
- `rectify_plates` 给出摆正的 BGR 图和 `transform`。交给 B 之前要转成 RGB。
- `color_hint` 不是最终颜色。

角色 B：代码已经在 `received/b/`。D 接入时还要遵守这些点：

- 输入是摆正后的单块车牌，不是整张原图。
- 颜色用返回值里的英文 `color`。中文「绿牌（新能源）」评测侧已当作 green。
- `count` 原样写入 `char_count`。`count_abnormal` 和 `no_char` 不要改成 7 或 8。
- `boxes` 在高度 140 像素的归一化图上，不能当作原图定位框。
- 字符图是 40×20、白笔画黑背景、从左到右，给 C 用。

角色 C：代码已经在 `received/c/`。

- `CharacterRecognizer.recognize_chars` 吃有序字符图，返回 `text`、`status` 和每个字的 `label`、`similarity`。
- 65 类，没有学、警、港、澳等特殊字。
- 包内训练图和 `evaluation_data` 是 C 自己的划分，还没有并进 `data/splits/manifest.json`。正式建库仍然不能使用终测图。

角色 D：https://github.com/bawangloong/plate-recognition-submit 的 main 上已有根目录 `pipeline.run(image_path)`。本仓库根目录没有这份文件，不带 `--pipeline` 时仍报 `pipeline missing`。

- 空的 `plates` 表示没有车牌。
- `evaluate.py` 把 `bbox`（长度为 4 的列表，或 `{x,y,w,h}`）收成 `box`，把 `color.color` 收成颜色字符串，把 `segmentation.count` 收成 `char_count`，把 `text` 收成 `number`。旧字段同时存在时优先用旧字段。
- `received/d/` 仍是当时收下的副本。那里没有把 A 放进 `vendor/a_plate/`。Windows `runtime/` 不在本仓库。

角色 E 自己还要补上，才能出表：

- 图像已经放进四个目录，JSONL 标注和清单已写好。来源记在每条 `source`。
- 验证集和终测集都有无牌、多牌、蓝黄绿白黑、倾斜、模糊和反光。模糊图的号码不可读，不参与逐字和整牌。
- `python3 data/check_dataset.py` 已通过：没有完全重复、近似重复或跨划分泄漏。
- 终测名单已经冻结。`python3 eval/evaluate.py --pipeline` 的这次结果在 `eval/results/system-evaluation.json`。夹具分数和 8 张合成样本不能抄进这张表。

## 报告

`docs/course/报告.md` 已按仓库里的 A–D 说明和冻结评测写成。分工按实际落地的代码写：E 做数据、评测和这份组装。课程表只有 `eval/results/system-evaluation.json` 里的数字。

## 幻灯片

`docs/course/slides.pptx` 共 12 页，按数据流和那张测试表排。没有界面截图，也没有夹具分数。

## 5 分钟视频

`docs/course/讲解稿.md` 是口播稿，约 4 分 45 秒。本仓库没有视频文件，也没有在镜头前重开 GUI。若以后补拍，演示用 development，正式数字仍来自冻结的 final_test。镜头里应看到无牌、多牌和错误文件类型。

## 最终 ZIP

课程要求一个小组 ZIP，里面有代码、报告和 5 分钟以内的视频。视频文件还没有，所以本分支没有放入完整 ZIP。各文件应放哪里写在 `docs/course/提交清单.md`。

- 代码：A–D 在 `received/`，数据和评测在 `data/`、`eval/`。系统入口在提交仓库，不在本仓库根目录。
- `received/d/车牌识别系统.exe` 只是启动器。完整 `runtime/` 未入库。
- 第二台 Windows 电脑的复测表仍是空的。材料里不写“已在另一台电脑测过 exe”。
- 私人车牌照片不要打进以后的 ZIP。

截止日期按课程页面的第 12 周。过期按作业说明处理。不要在材料里填写还没有跑出来的识别率。
