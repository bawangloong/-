# 角色 E 交接清单

仓库里现在有数据约定、评测入口、这份清单，以及 A、B、C、D 交来的代码，分别在 `received/a/`、`received/b/`、`received/c/`、`received/d/`。测试表、大作业报告、讲解幻灯片、5 分钟以内的视频和最终 ZIP 都还不能做。各组自己文档里的数字不要抄进课程测试表。

作业要求来自课程大作业：检测是否有车牌、定位并给出车牌图、分割后与字符库匹配、输出颜色和字符数及识别结果，并准备 GUI、exe、报告、视频和一份小组 ZIP。视频要讲原理、运行逻辑、实际演示和异常处理，时长不超过 5 分钟。报告要写小组分工。

## 已经有的

- 空的数据目录、标注字段和四档固定划分。
- `data/check_dataset.py`：字段、划分泄漏、完全重复和近似重复。
- `eval/evaluate.py`：流水线不在时明确退出；合成夹具只验证指标算术。
- 指标口径：`eval/README.md`。
- A 的检测和矫正：`received/a/`。说明见 `received/a/INTAKE.md`。
- B 的颜色识别和字符分割：`received/b/`。说明见 `received/b/INTAKE.md`。
- C 的字符库和识别：`received/c/`。说明见 `received/c/INTAKE.md`。
- D 的界面和流水线：`received/d/`。说明见 `received/d/INTAKE.md`。Windows 运行时因为单文件超过 GitHub 限制，没有放进仓库。

## 测试表之前

测试表指 validation / final_test 上的定位、颜色、字数、逐字、整牌和耗时。正式清单还是空的，D 的结果字段也还没接到 `evaluate.py`，所以没有表。

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

- 有许可的图像，放进四个目录，写好 JSONL 标注和清单。
- 验证集和终测集都要覆盖无牌、多牌、各颜色、倾斜、模糊、反光。
- 运行 `python data/check_dataset.py`，处理完全重复、近似重复和跨划分泄漏。
- 终测名单冻结后再跑 `python eval/evaluate.py`。在此之前不要把夹具分数抄进表里。

## 报告之前

- A–D 各自的方法说明：做了什么、输入输出、已知失败情况。E 不替他们写算法章节。
- 小组分工段落所需要的每人实际工作。课程要求报告包含分工。
- 一次真实评测的 JSON 输出，用来做表。没有这次运行，报告里就不写识别率。
- 数据来源和许可，写在标注的 `source` 里，报告直接引用。

E 负责把数据、划分、指标定义和这次真实运行写进报告。算法细节等 A–D 的文字到位再整合。

## 幻灯片之前

- 一张能讲清数据流的图：原图到框，到校正图，到颜色和字符，再到字库匹配。材料来自 A–D，E 只排进讲解结构。
- 真实运行的界面或命令行截图，至少包括有牌、无牌、多牌。
- 异常输入怎么处理。幻灯片不使用夹具的对照分数。

## 5 分钟视频之前

- 可运行的系统，能在镜头前打开本地图像并出结果。
- 讲稿覆盖原理、运行顺序、现场演示、异常处理，并且控制在 5 分钟以内。
- 演示用图不要临时从终测里抽走；演示集用 development，正式数字仍来自冻结的 final_test。
- 现场要能看到：没有车牌、一张图多块牌、错误的文件类型。这三项没有系统时无法拍摄。

## 最终 ZIP 之前

课程要求一个小组交一份 ZIP，里面有代码、报告，以及 5 分钟以内的讲解视频。系统还要能给别人运行，作业里写了 GUI 和 exe。

- 代码：A–D 的实现加上本分支的数据和评测脚本。
- 报告和视频：上面两项完成之后再放进去。
- GUI 和 exe：约定的 A–D 接口里没有这两项，本分支不实现。打包前需要小组指定负责人，把可运行程序交给 E。
- 异常文件类型、空文件、不支持的扩展名、过大或过小的图：等程序可运行后再测。现在没有这项结果。
- 私人车牌照片不要打进 ZIP。大型数据如果许可不允许再分发，ZIP 里只保留标注说明和代码，按课程对数据的要求处理。

截止日期按课程页面的第 12 周。过期按作业说明处理。不要在材料里填写还没有跑出来的识别率。
