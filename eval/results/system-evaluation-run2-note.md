# 第二次系统评测（新的一次运行）

这是另一次 `python3 eval/evaluate.py`，不是对 `eval/results/system-evaluation.json` 的修改。那份结果和课程报告里的旧数字都没有改。清单、标注和 final_test 图像也没有改。

命令：

```bash
python3 eval/evaluate.py --pipeline /agent/repos/plate-recognition-submit/pipeline.py --output eval/results/system-evaluation-run2.json
```

流水线提交：`d2ea549aa17216429d6a1a1f6fcfeb810f083663`（`plate-recognition-submit` 分支 `cursor/fix-detect-segment-f126`，基于上次的 `d7e9d13`）。这次检出里有 `vendor/a_plate`，框的 `source` 是 `a_module`。上次没有这个目录，用的是仓库自带检测。

号码为空的牌仍然不进入逐字和整牌。夹具分数和 8 张合成样本没有用在这里。IoU 阈值仍是 0.5。图像仍是 validation 加 final_test，共 17 张。

| 指标 | 上次 d7e9d13 | 这次 d2ea549 |
| --- | --- | --- |
| 车牌是否存在 | 9/17 | 12/17 |
| 定位精确率 | 5/22 | 9/16 |
| 定位召回率 | 5/19 | 9/19 |
| 定位 TP/FP/FN | 5/17/14 | 9/7/10 |
| 颜色（命中后） | 5/5 | 9/9 |
| 字符数量（命中后） | 1/5 | 5/9 |
| 逐字（定位命中后） | 4/35 | 37/63 |
| 逐字（端到端） | 4/115 | 37/115 |
| 整牌（定位命中后） | 0/5 | 3/9 |
| 整牌（端到端） | 0/16 | 3/16 |
| 运行时间 | 17 张，总和 2.952784 秒，平均 0.173693 秒，中位数 0.193764 秒，p95 0.421608 秒 | 17 张，总和 1.570579 秒，平均 0.092387 秒，中位数 0.069402 秒，p95 0.395130 秒 |

端到端整牌从 0/16 升到 3/16。三块对上的牌是终测 `皖AUJ299`、`粤B12345D`、`粤B12345F`。逐图和失败模块在 `system-evaluation-run2.md`。
