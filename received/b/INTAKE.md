# 角色 E 收下的 B 模块

这是 B 同学交来的压缩包，按原样放在 `received/b/`。E 没有改 `plate_color.py`、`segment_chars.py`、`run_demo.py`、`make_test_plates.py`。

在 `received/b/` 目录里运行：

```bash
python run_demo.py
```

依赖是 numpy 和 Pillow，不需要 OpenCV。需要先进入这个目录，因为脚本用相对路径找 `samples/` 和 `output/`。

## 和评测约定怎么接

B 的输入是**已经裁好的一块车牌**，不是整张街景。检测和摆正仍然要等 A。D 写 `pipeline.py` 时，对每块摆正的车牌调用：

```python
from plate_color import classify_plate_color, is_dark_text_on_light_plate
from segment_chars import segment_plate

color = classify_plate_color(rgb)["color"]   # blue / yellow / green / white / black / unknown
seg = segment_plate(rgb, prefer_dark_text=is_dark_text_on_light_plate(color))
# seg["count"]   实际字符数
# seg["status"]  ok / count_abnormal / no_char
# seg["chars"]   从左到右，40×20，白笔画、黑背景
```

交给 `evaluate.py` 时，颜色用上面的英文 `color`。中文名 `label` 里绿色写成「绿牌（新能源）」，评测别名已经收下这个写法。

`seg["boxes"]` 是高度归一化到 140 像素之后的坐标，不是原图坐标，也不能拿来算定位 IoU。定位框仍要 A 在原图上给。

`status` 为 `count_abnormal` 或 `no_char` 时，字符数仍然用 `count` 填进 `char_count`，不要改成 7 或 8。

## 他们附带的汇总

`output/summary.csv` 是 B 用 `make_test_plates.py` 生成的 6 张合成牌做的自测。E 在收下时用包里的 `samples/` 重跑了 `run_demo.py`，颜色、字符数和状态与这张表一致。

这 6 张图不在 `data/splits/manifest.json` 里，也不是 validation 或 final_test。表里的对错不能写进课程测试表、报告或幻灯片。倾斜那张他们自己标成字符数 5、`count_abnormal`，并说明摆正要由 A 做。
