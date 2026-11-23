# D 模块测试记录

测试日期：2026-11-19
测试环境：Windows 11 家庭中文版 25H2（build 26200）/ Python 3.13.7 / numpy 2.3.5 /
opencv-contrib-python 5.0.0.93 / Pillow 12.0.0

## 一、功能测试（合成演示图）

命令：`python tools/smoke_test.py`

| # | 图片 | 场景 | 车牌数 | 颜色 | 字符数 | 识别结果 | 结果 | 耗时 |
|---|---|---|---|---|---|---|---|---|
| 1 | normal_blue.png | 正常蓝牌 | 1 | 蓝 | 7 | 京A12345 | 正确 | 145 ms |
| 2 | tilt_yellow.png | 倾斜 13° 黄牌 | 1 | 黄 | 7 | 粤B88888 | 正确 | 81 ms |
| 3 | multi_two.png | 双车牌（绿+蓝） | 2 | 绿/蓝 | 8/7 | 沪AD12345 / 京A12345 | 正确 | 131 ms |
| 4 | green_8.png | 新能源 8 位 | 1 | 绿 | 8 | 沪AD12345 | 正确 | 77 ms |
| 5 | black_plate.png | 黑牌 | 1 | 黑 | 7 | 蒙A88888 | 省份错（真值京） | 79 ms |
| 6 | large_3000.jpg | 3000×2000 大图 | 1 | 蓝 | 7 | 京A12345 | 正确 | 128 ms |
| 7 | no_plate.png | 无车牌 | 0 | — | — | — | 正确提示 | 35 ms |
| 8 | blur_glare.png | 模糊+强反光白牌 | 0 | — | — | — | 漏检（已知问题） | 33 ms |

统计（不含无车牌图）：7 张有车牌图片检出 6 张；检出的 7 块车牌中 6 块号码
完全正确；字符数 7/7 正确。

## 二、异常处理测试

| 用例 | 操作 | 预期 | 实际 |
|---|---|---|---|
| 取消选图 | 打开文件对话框后点“取消” | 无报错，日志记录 | 通过 |
| 非图片类型 | `note.txt` 改名为 `.txt` 选择 | `unsupported_type` 弹窗 | 通过 |
| 损坏图片 | 写坏 PNG 头 | `decode_failed` 弹窗 | 通过 |
| 空文件 | 0 字节 `.png` | `empty_file` 弹窗 | 通过 |
| 中文路径 | `中文目录/测试图片 京A12345.png` | 正常识别 | 通过 |
| 无车牌 | 纯场景图 | 弹窗“未检测到车牌” | 通过 |
| 字符数异常 | 7 位/8 位以外 | 提示“字符数异常”，仍给参考结果 | 通过 |
| 识别中取消 | 点“取消” | 当前结果丢弃，按钮恢复 | 通过 |
| 识别中关闭 | 点窗口 × | 二次确认 | 通过 |
| 字符库缺失 | 重命名 `library.npz` | 启动提示缺失 | 通过 |

## 三、回归测试

命令：`python -m unittest discover -s tests -v`

```
test_blue_plate ......... ok
test_chinese_path ....... ok
test_corrupt_image ...... ok
test_new_energy_8_chars . ok
test_no_plate ........... ok
test_unsupported_type ... ok
Ran 6 tests ... OK
```

## 四、GUI 检查

用 `tools/gui_smoke.py` 注入图片与结果、截图检查：

- 1280×820 默认窗口，1024×680 最小窗口均无控件重叠；
- 多车牌按钮切换后号码、颜色、字符数、过程图同步刷新；
- 字符网格 7 个/行，超出换行；低分字符分数标红；
- 原图框选位置与车牌列表序号一致；
- 识别期间窗口可拖动，取消按钮可用。

截图：`docs/gui_screenshot.png`（识别结果）、`docs/gui_process.png`（处理过程）、
`docs/exe_running.png`（绿色包启动）。

## 五、打包后验证

| 项目 | 结果 |
|---|---|
| 清空 PATH 后 `runtime\python.exe -m app.cli samples\normal_blue.png` | 京A12345，通过 |
| 清空 PATH 后启动 GUI | 标题“车牌识别系统 v1.0.0”，通过 |
| 绿色包目录完整性 | `runtime/`、`vendor/`、`app_main.py`、exe 齐全 |
| 发行包大小 | 211.3 MB（压缩后约 82 MB） |
| 第二台物理电脑 | 待复测，见 `docs/另一台电脑测试记录.md` |
