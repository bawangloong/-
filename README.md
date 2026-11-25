# 车牌识别大作业

小组作业：用 Python 和 OpenCV 做车牌检测、校正、颜色、字符分割，再和字符库匹配。

这里有角色 E 的数据约定、评测入口、交接清单，以及已经收到的 A、B、C、D 模块。仓库根目录还没有 `evaluate.py` 能直接调用的 `pipeline.py`。

| 材料 | 位置 |
| --- | --- |
| 数据布局、标注和划分 | `data/README.md` |
| 重复与字段检查 | `python data/check_dataset.py` |
| 指标口径 | `eval/README.md` |
| 评测入口 | `python eval/evaluate.py` |
| 指标算术的合成夹具 | `python eval/evaluate.py --fixture` |
| 已收到的 A 模块（检测和矫正） | `received/a/INTAKE.md` |
| 已收到的 B 模块（颜色和字符分割） | `received/b/INTAKE.md` |
| 已收到的 C 模块（字符库和识别） | `received/c/INTAKE.md` |
| 已收到的 D 模块（界面和流水线） | `received/d/INTAKE.md` |
| 课程测试表 | `eval/results/system-evaluation.json` |
| 课程报告、幻灯片、讲解稿、提交清单 | `docs/course/` |
| 出视频和完整 ZIP 之前还缺什么 | `docs/handoff-checklist.md` |

夹具打印的数字只对照指标代码，不是系统实测。正式图像在 `data/raw/`。仓库根目录没有 `pipeline.py`，评测时用 `--pipeline` 指向提交仓库。课程数字以 `eval/results/system-evaluation.json` 那一次运行为准。
