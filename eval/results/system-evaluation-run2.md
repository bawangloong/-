# 课程测试结果

这是新的一次运行，写在本文件和 `system-evaluation-run2.json`。不替换 `system-evaluation.json`，也不改课程报告里的旧数字。和上次的对照见 `system-evaluation-run2-note.md`。流水线提交 `d2ea549aa17216429d6a1a1f6fcfeb810f083663`。

这次数字只来自 `eval/evaluate.py` 对冻结清单里 validation 和 final_test 的一次 `pipeline.run`。
夹具分数和提交仓库的 8 张合成样本没有用在这里。号码归一化后为空的标注不参与逐字和整牌。

- 流水线：`/agent/repos/plate-recognition-submit/pipeline.py`


- 划分：validation, final_test
- IoU 阈值：0.5
- 图像 17，调用错误 0
- 标注车牌 19，预测车牌 16

## 指标

| 指标 | 结果 |
| --- | --- |
| 车牌是否存在 | 12/17（0.705882） |
| 定位精确率 | 9/16（0.562500） |
| 定位召回率 | 9/19（0.473684） |
| 颜色 | 9/9（1.000000） |
| 字符数量 | 5/9（0.555556） |
| 逐字（定位命中后） | 37/63（0.587302） |
| 逐字（端到端） | 37/115（0.321739） |
| 整牌（定位命中后） | 3/9（0.333333） |
| 整牌（端到端） | 3/16（0.187500） |
| 运行时间 | 17 张，总和 1.570579 秒，平均 0.092387 秒，中位数 0.069402 秒，p95 0.395130 秒 |

## 逐图

| 划分 | 图像 | 有牌 | 预测块数 | TP/FP/FN | 标注号码 | 预测号码 | 耗时（秒） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | val_ccpd_0 | 有 | 2 | 1/1/0 | 皖A195K9 | A1赣9 | 0.395130 |
| validation | val_diplomatic | 有 | 0 | 0/0/1 | 127002使 | 未配上 | 0.046670 |
| validation | val_yellow_bike | 有 | 0 | 0/0/1 | 京东城0003934 | 未配上 | 0.026094 |
| validation | val_green_shanghai | 有 | 2 | 0/2/1 | 沪AF22933 | 未配上 | 0.120237 |
| validation | val_multi_hk | 有 | 1 | 1/0/3 | 粤ZC839澳<br>MJ2882<br>ZM1433<br>（空，不参与识别率） | 未配上<br>未配上<br>1433<br>未配上 | 0.100440 |
| validation | val_military_glare | 有 | 2 | 0/2/1 | VA01940 | 未配上 | 0.210606 |
| validation | val_blur_california | 有 | 0 | 0/0/1 | （空，不参与识别率） | 未配上 | 0.001666 |
| validation | val_empty_aerial | 无 | 1 | 0/1/0 | 无 | 无 | 0.063375 |
| final_test | fin_ccpd_1 | 有 | 1 | 1/0/0 | 皖AUJ299 | 皖AUJ299 | 0.053411 |
| final_test | fin_ccpd_4 | 有 | 1 | 1/0/0 | 皖A256R2 | 皖A冀6冀2 | 0.067737 |
| final_test | fin_green_rickshaw | 有 | 1 | 1/0/0 | 西城0414 | 黑冀0414 | 0.084860 |
| final_test | fin_yellow_shaanxi | 有 | 1 | 1/0/0 | 陕AA9087 | 蒙黑AAA9087 | 0.078945 |
| final_test | fin_military_hg | 有 | 1 | 1/0/0 | HG05015 | 甘G05015 | 0.069402 |
| final_test | fin_diplomatic | 有 | 0 | 0/0/1 | 使132003 | 未配上 | 0.012687 |
| final_test | fin_green_large | 有 | 2 | 2/0/0 | 粤B12345D<br>粤B12345F | 粤B12345D<br>粤B12345F | 0.106155 |
| final_test | fin_blur_motorcycle | 有 | 1 | 0/1/1 | （空，不参与识别率） | 未配上 | 0.101087 |
| final_test | fin_empty_lot | 无 | 0 | 0/0/0 | 无 | 无 | 0.032078 |

## 失败

号码为空的牌不会出现在逐字或整牌行里。模块只在输出字段写明阶段时填写。

| 图像 | 项目 | 期望 | 实际 | 模块 | 依据 |
| --- | --- | --- | --- | --- | --- |
| val_ccpd_0 | 字符数量 | 7 | 4 | 字符分割（B） | segmentation.count=4 status=count_abnormal message=分割出 4 个字符（常见为 7 或 8 个） |
| val_ccpd_0 | 逐字 | 皖A195K9 | A1赣9 | 字符分割（B） | segmentation.status=count_abnormal count=4；recognition.status=ok text=A1赣9；错位 0:皖->A, 1:A->1, 2:1->赣, 4:5->缺, 5:K->缺, 6:9->缺 |
| val_ccpd_0 | 整牌 | 皖A195K9 | A1赣9 | 字符分割（B） | segmentation.status=count_abnormal count=4；recognition.status=ok text=A1赣9 |
| val_ccpd_0 | 定位误检 | 无对应标注框 | {"x": 84, "y": 0, "w": 140, "h": 72} | 检测 | source=a_module |
| val_diplomatic | 车牌是否存在 | True | False | 检测 | 未检测到车牌 |
| val_diplomatic | 定位 | {"x": 400, "y": 340, "w": 560, "h": 210} | 未配上 | 检测 | 未检测到车牌 |
| val_diplomatic | 整牌（端到端） | 127002使 |  | 检测 | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 未检测到车牌 |
| val_yellow_bike | 车牌是否存在 | True | False | 检测 | 未检测到车牌 |
| val_yellow_bike | 定位 | {"x": 390, "y": 300, "w": 680, "h": 620} | 未配上 | 检测 | 未检测到车牌 |
| val_yellow_bike | 整牌（端到端） | 京东城0003934 |  | 检测 | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 未检测到车牌 |
| val_green_shanghai | 定位 | {"x": 400, "y": 600, "w": 430, "h": 160} | 未配上 |  |  |
| val_green_shanghai | 整牌（端到端） | 沪AF22933 |  |  | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 |
| val_green_shanghai | 定位误检 | 无对应标注框 | {"x": 1257, "y": 450, "w": 143, "h": 79} | 检测 | source=a_module |
| val_green_shanghai | 定位误检 | 无对应标注框 | {"x": 641, "y": 653, "w": 160, "h": 35} | 检测 | source=a_module |
| val_multi_hk | 字符数量 | 6 | 4 | 字符分割（B） | segmentation.count=4 status=count_abnormal message=分割出 4 个字符（常见为 7 或 8 个） |
| val_multi_hk | 逐字 | ZM1433 | 1433 | 字符分割（B） | segmentation.status=count_abnormal count=4；recognition.status=ok text=1433；错位 0:Z->1, 1:M->4, 2:1->3, 3:4->3, 4:3->缺, 5:3->缺 |
| val_multi_hk | 整牌 | ZM1433 | 1433 | 字符分割（B） | segmentation.status=count_abnormal count=4；recognition.status=ok text=1433 |
| val_multi_hk | 定位 | {"x": 600, "y": 540, "w": 300, "h": 95} | 未配上 |  |  |
| val_multi_hk | 整牌（端到端） | 粤ZC839澳 |  |  | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 |
| val_multi_hk | 定位 | {"x": 610, "y": 625, "w": 285, "h": 57} | 未配上 |  |  |
| val_multi_hk | 整牌（端到端） | MJ2882 |  |  | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 |
| val_multi_hk | 定位 | {"x": 1260, "y": 455, "w": 140, "h": 100} | 未配上 |  |  |
| val_military_glare | 定位 | {"x": 500, "y": 760, "w": 400, "h": 140} | 未配上 |  |  |
| val_military_glare | 整牌（端到端） | VA01940 |  |  | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 |
| val_military_glare | 定位误检 | 无对应标注框 | {"x": 602, "y": 796, "w": 294, "h": 84} | 检测 | source=a_module |
| val_military_glare | 定位误检 | 无对应标注框 | {"x": 976, "y": 0, "w": 420, "h": 100} | 检测 | source=a_module |
| val_blur_california | 车牌是否存在 | True | False | 检测 | 未检测到车牌 |
| val_blur_california | 定位 | {"x": 0, "y": 0, "w": 327, "h": 75} | 未配上 | 检测 | 未检测到车牌 |
| val_empty_aerial | 车牌是否存在 | False | True | 检测 | source=a_module |
| val_empty_aerial | 定位误检 | 无对应标注框 | {"x": 0, "y": 0, "w": 134, "h": 39} | 检测 | source=a_module |
| fin_ccpd_4 | 字符数量 | 7 | 6 | 字符分割（B） | segmentation.count=6 status=count_abnormal message=分割出 6 个字符（常见为 7 或 8 个） |
| fin_ccpd_4 | 逐字 | 皖A256R2 | 皖A冀6冀2 | 字符分割（B） | segmentation.status=count_abnormal count=6；recognition.status=needs_review text=皖A冀6冀2；错位 2:2->冀, 3:5->6, 4:6->冀, 5:R->2, 6:2->缺 |
| fin_ccpd_4 | 整牌 | 皖A256R2 | 皖A冀6冀2 | 字符分割（B） | segmentation.status=count_abnormal count=6；recognition.status=needs_review text=皖A冀6冀2 |
| fin_green_rickshaw | 逐字 | 西城0414 | 黑冀0414 | 字符识别（C） | recognition.status=needs_review text=黑冀0414；segmentation.status=count_abnormal count=6；错位 0:西->黑, 1:城->冀 |
| fin_green_rickshaw | 整牌 | 西城0414 | 黑冀0414 | 字符识别（C） | recognition.status=needs_review text=黑冀0414；segmentation.status=count_abnormal count=6 |
| fin_yellow_shaanxi | 字符数量 | 7 | 9 | 字符分割（B） | segmentation.count=9 status=count_abnormal message=分割出 9 个字符（常见为 7 或 8 个） |
| fin_yellow_shaanxi | 逐字 | 陕AA9087 | 蒙黑AAA9087 | 字符分割（B） | segmentation.status=count_abnormal count=9；recognition.status=needs_review text=蒙黑AAA9087；错位 0:陕->蒙, 1:A->黑, 3:9->A, 4:0->A, 5:8->9, 6:7->0 |
| fin_yellow_shaanxi | 整牌 | 陕AA9087 | 蒙黑AAA9087 | 字符分割（B） | segmentation.status=count_abnormal count=9；recognition.status=needs_review text=蒙黑AAA9087 |
| fin_military_hg | 逐字 | HG05015 | 甘G05015 | 字符识别（C） | recognition.status=needs_review text=甘G05015；错位 0:H->甘 |
| fin_military_hg | 整牌 | HG05015 | 甘G05015 | 字符识别（C） | recognition.status=needs_review text=甘G05015 |
| fin_diplomatic | 车牌是否存在 | True | False | 检测 | 未检测到车牌 |
| fin_diplomatic | 定位 | {"x": 10, "y": 8, "w": 1380, "h": 464} | 未配上 | 检测 | 未检测到车牌 |
| fin_diplomatic | 整牌（端到端） | 使132003 |  | 检测 | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 未检测到车牌 |
| fin_blur_motorcycle | 定位 | {"x": 70, "y": 720, "w": 130, "h": 100} | 未配上 |  |  |
| fin_blur_motorcycle | 定位误检 | 无对应标注框 | {"x": 243, "y": 407, "w": 85, "h": 29} | 检测 | source=a_module |
