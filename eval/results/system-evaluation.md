# 课程测试结果

这次数字只来自 `eval/evaluate.py` 对冻结清单里 validation 和 final_test 的一次 `pipeline.run`。
夹具分数和提交仓库的 8 张合成样本没有用在这里。号码归一化后为空的标注不参与逐字和整牌。

- 流水线：`/tmp/plate-recognition-submit/pipeline.py`
- 流水线提交：`d7e9d13c6ed0361f9b7cebeefa9d0eb59d3c7ec3`
- 克隆的提交仓库没有 vendor/a_plate。检出框的 source 为 color:* 或 gradient，来自仓库自带的内置检测。
- 划分：validation, final_test
- IoU 阈值：0.5
- 图像 17，调用错误 0
- 标注车牌 19，预测车牌 22

## 指标

| 指标 | 结果 |
| --- | --- |
| 车牌是否存在 | 9/17（0.529412） |
| 定位精确率 | 5/22（0.227273） |
| 定位召回率 | 5/19（0.263158） |
| 颜色 | 5/5（1.000000） |
| 字符数量 | 1/5（0.200000） |
| 逐字（定位命中后） | 4/35（0.114286） |
| 逐字（端到端） | 4/115（0.034783） |
| 整牌（定位命中后） | 0/5（0.000000） |
| 整牌（端到端） | 0/16（0.000000） |
| 运行时间 | 17 张，总和 2.952784 秒，平均 0.173693 秒，中位数 0.193764 秒，p95 0.421608 秒 |

## 逐图

| 划分 | 图像 | 有牌 | 预测块数 | TP/FP/FN | 标注号码 | 预测号码 | 耗时（秒） |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | val_ccpd_0 | 有 | 0 | 0/0/1 | 皖A195K9 | 未配上 | 0.421608 |
| validation | val_diplomatic | 有 | 0 | 0/0/1 | 127002使 | 未配上 | 0.155371 |
| validation | val_yellow_bike | 有 | 2 | 0/2/1 | 京东城0003934 | 未配上 | 0.196243 |
| validation | val_green_shanghai | 有 | 1 | 0/1/1 | 沪AF22933 | 未配上 | 0.193764 |
| validation | val_multi_hk | 有 | 3 | 1/2/3 | 粤ZC839澳<br>MJ2882<br>ZM1433<br>（空，不参与识别率） | 未配上<br>未配上<br>1A豫<br>未配上 | 0.220547 |
| validation | val_military_glare | 有 | 1 | 0/1/1 | VA01940 | 未配上 | 0.214103 |
| validation | val_blur_california | 有 | 0 | 0/0/1 | （空，不参与识别率） | 未配上 | 0.001097 |
| validation | val_empty_aerial | 无 | 3 | 0/3/0 | 无 | 无 | 0.214424 |
| final_test | fin_ccpd_1 | 有 | 0 | 0/0/1 | 皖AUJ299 | 未配上 | 0.158163 |
| final_test | fin_ccpd_4 | 有 | 1 | 0/1/1 | 皖A256R2 | 未配上 | 0.175353 |
| final_test | fin_green_rickshaw | 有 | 3 | 1/2/0 | 西城0414 | 晋冀0414 | 0.249979 |
| final_test | fin_yellow_shaanxi | 有 | 1 | 1/0/0 | 陕AA9087 | A冀渝7 | 0.108346 |
| final_test | fin_military_hg | 有 | 0 | 0/0/1 | HG05015 | 未配上 | 0.012313 |
| final_test | fin_diplomatic | 有 | 0 | 0/0/1 | 使132003 | 未配上 | 0.093305 |
| final_test | fin_green_large | 有 | 2 | 2/0/0 | 粤B12345D<br>粤B12345F | 12345D<br>12345F | 0.088190 |
| final_test | fin_blur_motorcycle | 有 | 2 | 0/2/1 | （空，不参与识别率） | 未配上 | 0.252920 |
| final_test | fin_empty_lot | 无 | 3 | 0/3/0 | 无 | 无 | 0.197058 |

## 失败

号码为空的牌不会出现在逐字或整牌行里。模块只在输出字段写明阶段时填写。

| 图像 | 项目 | 期望 | 实际 | 模块 | 依据 |
| --- | --- | --- | --- | --- | --- |
| val_ccpd_0 | 车牌是否存在 | True | False | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_ccpd_0 | 定位 | {"x": 240, "y": 490, "w": 240, "h": 100} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_ccpd_0 | 整牌（端到端） | 皖A195K9 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_diplomatic | 车牌是否存在 | True | False | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_diplomatic | 定位 | {"x": 400, "y": 340, "w": 560, "h": 210} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_diplomatic | 整牌（端到端） | 127002使 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_yellow_bike | 定位 | {"x": 390, "y": 300, "w": 680, "h": 620} | 未配上 | 集成过滤（D） | 第 2 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_yellow_bike | 整牌（端到端） | 京东城0003934 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 2 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_yellow_bike | 定位误检 | 无对应标注框 | {"x": 858, "y": 0, "w": 51, "h": 15} | 检测 | source=color:yellow |
| val_yellow_bike | 定位误检 | 无对应标注框 | {"x": 473, "y": 589, "w": 560, "h": 231} | 检测 | source=gradient |
| val_green_shanghai | 定位 | {"x": 400, "y": 600, "w": 430, "h": 160} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_green_shanghai | 整牌（端到端） | 沪AF22933 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_green_shanghai | 定位误检 | 无对应标注框 | {"x": 0, "y": 517, "w": 39, "h": 17} | 检测 | source=color:blue |
| val_multi_hk | 字符数量 | 6 | 3 | 字符分割（B） | segmentation.count=3 status=count_abnormal message=分割出 3 个字符（常见为 7 或 8 个） |
| val_multi_hk | 逐字 | ZM1433 | 1A豫 | 字符分割（B） | segmentation.status=count_abnormal count=3；错位 0:Z->1, 1:M->A, 2:1->豫, 3:4->缺, 4:3->缺, 5:3->缺 |
| val_multi_hk | 整牌 | ZM1433 | 1A豫 | 字符分割（B） | segmentation.status=count_abnormal count=3 |
| val_multi_hk | 定位 | {"x": 600, "y": 540, "w": 300, "h": 95} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃 |
| val_multi_hk | 整牌（端到端） | 粤ZC839澳 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃 |
| val_multi_hk | 定位 | {"x": 610, "y": 625, "w": 285, "h": 57} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃 |
| val_multi_hk | 整牌（端到端） | MJ2882 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃 |
| val_multi_hk | 定位 | {"x": 1260, "y": 455, "w": 140, "h": 100} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃 |
| val_multi_hk | 定位误检 | 无对应标注框 | {"x": 278, "y": 282, "w": 77, "h": 32} | 检测 | source=color:yellow |
| val_multi_hk | 定位误检 | 无对应标注框 | {"x": 602, "y": 566, "w": 144, "h": 55} | 检测 | source=color:blue |
| val_military_glare | 定位 | {"x": 500, "y": 760, "w": 400, "h": 140} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_military_glare | 整牌（端到端） | VA01940 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| val_military_glare | 定位误检 | 无对应标注框 | {"x": 304, "y": 92, "w": 120, "h": 37} | 检测 | source=color:blue |
| val_blur_california | 车牌是否存在 | True | False | 检测 | 未检测到车牌 |
| val_blur_california | 定位 | {"x": 0, "y": 0, "w": 327, "h": 75} | 未配上 | 检测 | 未检测到车牌 |
| val_empty_aerial | 车牌是否存在 | False | True | 检测 | source=color:green,color:yellow,color:yellow |
| val_empty_aerial | 定位误检 | 无对应标注框 | {"x": 203, "y": 154, "w": 926, "h": 393} | 检测 | source=color:green |
| val_empty_aerial | 定位误检 | 无对应标注框 | {"x": 1100, "y": 747, "w": 100, "h": 22} | 检测 | source=color:yellow |
| val_empty_aerial | 定位误检 | 无对应标注框 | {"x": 559, "y": 784, "w": 79, "h": 15} | 检测 | source=color:yellow |
| fin_ccpd_1 | 车牌是否存在 | True | False | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| fin_ccpd_1 | 定位 | {"x": 180, "y": 490, "w": 230, "h": 100} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| fin_ccpd_1 | 整牌（端到端） | 皖AUJ299 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| fin_ccpd_4 | 定位 | {"x": 170, "y": 480, "w": 240, "h": 90} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃 |
| fin_ccpd_4 | 整牌（端到端） | 皖A256R2 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃；第 3 个候选区域识别置信度低，按误检丢弃 |
| fin_ccpd_4 | 定位误检 | 无对应标注框 | {"x": 658, "y": 1071, "w": 62, "h": 35} | 检测 | source=color:yellow |
| fin_green_rickshaw | 逐字 | 西城0414 | 晋冀0414 | 字符识别（C） | recognition.status=needs_review text=晋冀0414；segmentation.status=count_abnormal count=6，字数与标注同为 6；错位 0:西->晋, 1:城->冀 |
| fin_green_rickshaw | 整牌 | 西城0414 | 晋冀0414 | 字符识别（C） | recognition.status=needs_review text=晋冀0414；segmentation.status=count_abnormal count=6，字数与标注同为 6 |
| fin_green_rickshaw | 定位误检 | 无对应标注框 | {"x": 871, "y": 202, "w": 49, "h": 14} | 检测 | source=color:yellow |
| fin_green_rickshaw | 定位误检 | 无对应标注框 | {"x": 0, "y": 813, "w": 1400, "h": 237} | 检测 | source=color:yellow |
| fin_yellow_shaanxi | 字符数量 | 7 | 4 | 字符分割（B） | segmentation.count=4 status=count_abnormal message=分割出 4 个字符（常见为 7 或 8 个） |
| fin_yellow_shaanxi | 逐字 | 陕AA9087 | A冀渝7 | 字符分割（B） | segmentation.status=count_abnormal count=4；错位 0:陕->A, 1:A->冀, 2:A->渝, 3:9->7, 4:0->缺, 5:8->缺, 6:7->缺 |
| fin_yellow_shaanxi | 整牌 | 陕AA9087 | A冀渝7 | 字符分割（B） | segmentation.status=count_abnormal count=4 |
| fin_military_hg | 车牌是否存在 | True | False | 检测 | 未检测到车牌 |
| fin_military_hg | 定位 | {"x": 8, "y": 6, "w": 1384, "h": 395} | 未配上 | 检测 | 未检测到车牌 |
| fin_military_hg | 整牌（端到端） | HG05015 |  | 检测 | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 未检测到车牌 |
| fin_diplomatic | 车牌是否存在 | True | False | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃 |
| fin_diplomatic | 定位 | {"x": 10, "y": 8, "w": 1380, "h": 464} | 未配上 | 集成过滤（D） | 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃 |
| fin_diplomatic | 整牌（端到端） | 使132003 |  | 集成过滤（D） | 没有配上的预测框，端到端整牌算错；不进入定位命中后的识别率。 第 1 个候选区域识别置信度低，按误检丢弃；第 2 个候选区域识别置信度低，按误检丢弃 |
| fin_green_large | 字符数量 | 8 | 6 | 字符分割（B） | segmentation.count=6 status=count_abnormal message=分割出 6 个字符（常见为 7 或 8 个） |
| fin_green_large | 逐字 | 粤B12345D | 12345D | 字符分割（B） | segmentation.status=count_abnormal count=6；错位 0:粤->1, 1:B->2, 2:1->3, 3:2->4, 4:3->5, 5:4->D, 6:5->缺, 7:D->缺 |
| fin_green_large | 整牌 | 粤B12345D | 12345D | 字符分割（B） | segmentation.status=count_abnormal count=6 |
| fin_green_large | 字符数量 | 8 | 6 | 字符分割（B） | segmentation.count=6 status=count_abnormal message=分割出 6 个字符（常见为 7 或 8 个） |
| fin_green_large | 逐字 | 粤B12345F | 12345F | 字符分割（B） | segmentation.status=count_abnormal count=6；错位 0:粤->1, 1:B->2, 2:1->3, 3:2->4, 4:3->5, 5:4->F, 6:5->缺, 7:F->缺 |
| fin_green_large | 整牌 | 粤B12345F | 12345F | 字符分割（B） | segmentation.status=count_abnormal count=6 |
| fin_blur_motorcycle | 定位 | {"x": 70, "y": 720, "w": 130, "h": 100} | 未配上 | 集成过滤（D） | 第 3 个候选区域识别置信度低，按误检丢弃；第 4 个候选区域识别置信度低，按误检丢弃 |
| fin_blur_motorcycle | 定位误检 | 无对应标注框 | {"x": 0, "y": 0, "w": 1400, "h": 442} | 检测 | source=color:green |
| fin_blur_motorcycle | 定位误检 | 无对应标注框 | {"x": 240, "y": 406, "w": 90, "h": 32} | 检测 | source=color:yellow |
| fin_empty_lot | 车牌是否存在 | False | True | 检测 | source=color:green,color:green,color:yellow；第 2 个候选区域识别置信度低，按误检丢弃 |
| fin_empty_lot | 定位误检 | 无对应标注框 | {"x": 872, "y": 0, "w": 69, "h": 27} | 检测 | source=color:green |
| fin_empty_lot | 定位误检 | 无对应标注框 | {"x": 783, "y": 478, "w": 417, "h": 148} | 检测 | source=color:green |
| fin_empty_lot | 定位误检 | 无对应标注框 | {"x": 273, "y": 534, "w": 71, "h": 22} | 检测 | source=color:yellow |
