# 车牌识别大作业

小组作业：用 Python 和 OpenCV 做车牌检测、校正、颜色、字符分割，再和字符库匹配。

这里只放角色 E 的地基：数据约定、评测入口、交接清单。检测、校正、颜色、分割、字符库、识别和 `pipeline.py` 都不在这里。

| 材料 | 位置 |
| --- | --- |
| 数据布局、标注和划分 | `data/README.md` |
| 重复与字段检查 | `python data/check_dataset.py` |
| 指标口径 | `eval/README.md` |
| 评测入口 | `python eval/evaluate.py` |
| 指标算术的合成夹具 | `python eval/evaluate.py --fixture` |
| 出测试表、报告、幻灯片、视频和 ZIP 之前还缺什么 | `docs/handoff-checklist.md` |

夹具打印的数字只对照指标代码，不是系统实测。清单里还没有正式图像；没有 `pipeline.py` 时，评测脚本会说明流水线缺失并退出。
