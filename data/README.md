# 数据布局与标注

角色 E 的数据约定。这里没有车牌照片，也没有下载数据集。`data/schema/examples.json` 里的记录只是空模板，编号都以 `EXAMPLE_` 开头，不能写进清单。

## 目录

| 路径 | 用途 |
| --- | --- |
| `data/raw/development/` | 开发图像。检测、校正、分割、流水线调试可以用。 |
| `data/raw/library/` | 只给字符库切样本。 |
| `data/raw/validation/` | 调完后看指标。不能拿去建字符库。 |
| `data/raw/final_test/` | 最后一次评测。不能拿去建字符库，也不能看完结果再改算法重测。 |
| `data/annotations/annotations.jsonl` | 正式标注，一行一个 JSON。现在是空文件。 |
| `data/splits/manifest.json` | 固定四档划分。现在四个名单都是空的。 |
| `data/schema/` | 字段约定、JSON Schema 和示例。 |
| `data/check_dataset.py` | 检查字段、划分和重复图像。 |

图像放进对应的 `data/raw/<划分>/`。`relative_path` 从仓库根目录写起，形如 `data/raw/<purpose>/文件名`，并且 `purpose` 必须和清单里的划分相同。

正式标注从 `data/schema/examples.json` 抄一条，改掉 `EXAMPLE_` 编号，去掉 `_example` 和 `_comment`，再把 `image_id` 放进 `manifest.json` 的对应名单。不要把示例文件本身写进清单。

## 一条标注要有什么

每张图记录：

- `source`：来源。`origin` 取 `self_captured`、`public`、`synthetic`、`unknown`。还要写来源名称和许可；有网址就填 `url`。
- `purpose`：`development`、`library`、`validation`、`final_test` 四选一，并与路径、清单一致。
- `category`：情形标签，可以多个。
- `has_plate`：这张图有没有车牌。
- `plates`：每块牌的外接矩形、号码、颜色、字符数。没有牌就是空数组。

每块牌：

- `box`：原图像素，左上角为原点，`x` 向右，`y` 向下，宽 `w`，高 `h`。定位只认这个轴对齐外接矩形。
- `quad`：可选的四个角点，给倾斜车牌留档。评测不用它。
- `number`：完整号码，不写空格、中点或连字符。
- `color`：`blue`、`yellow`、`green`、`white`、`black`、`unknown`，或下面的中文别名。看不清就写 `unknown`，不要猜。
- `char_count`：字符个数。新能源牌可以是 8，普通牌通常是 7，不在这里把长度和颜色绑死。
- `chars`：可选，从左到右的单字符数组，拼起来必须等于 `number`。
- `readable`：号码是否可读。不可读且没有号码时，不参与逐字和整牌，颜色和字数仍可标。

颜色别名与 `eval/metrics.py` 里的闭集相同：蓝 / 蓝色 / 蓝牌，黄 / 黄色 / 黄牌，绿 / 绿色 / 绿牌 / 新能源 / 新能源绿，白 / 白色 / 白牌，黑 / 黑色 / 黑牌，未知 / 无法判断。

## 情形标签

有无车牌三选一：`no_plate`、`single_plate`、`multi_plate`。

已知颜色要有对应标签：`color_blue`、`color_yellow`、`color_green`、`color_white`、`color_black`。`unknown` 不加颜色标签。

成像条件：`tilt`、`blur`、`glare`。三者都没有、并且有车牌时，可以再标 `normal`。说不清的情况用 `other`。

`conditions.tilt`、`conditions.blur`、`conditions.glare` 必须和这些标签一致。

示例已经覆盖：无车牌、多车牌、五种颜色、显式未知颜色、倾斜、模糊、反光，以及四个划分。正式收数据时，验证集和终测集各自都要有这些情形，不能只堆在开发集里。

## 划分规则

四个名字是固定的。`development` 和 `library` 可以给对应角色使用。`evaluate.py` 默认只评 `validation` 和 `final_test`。

`library` 与 `validation`、`final_test` 不能有同一张图，也不能有近似重复。字符库样本和最终测试样本必须分开。开发集同样不要混进终测。

填进终测之后，不要再拿这些图调检测阈值、改字符模板或增补字符库。

## 重复检查

```bash
python data/check_dataset.py --self-test
python data/check_dataset.py
```

- 完全重复：文件字节的 SHA-256 相同。
- 近似重复：把图像缩成 8×8，灰度取 `(R+G+B)//3`，每个格大于等于 64 格平均值的记为 1。两个哈希的汉明距离小于等于 5 记为近似重复。阈值用 `--near-threshold` 改。
- 同一内容换了编码（例如 BMP 和 PNG）字节不同，但会被近似重复抓住。
- 跨划分的重复会单独标出。字符库对终测、开发集对终测、字符库对验证集都算问题。

PNG、BMP、PPM、PGM 用标准库解码。JPEG、WEBP、TIFF 需要本机已安装的 Pillow；没装时这些文件仍做完全重复检查，但近似哈希算不出，脚本以失败结束，避免漏掉近重复。平均哈希会漏掉一些只改颜色的图，它是筛查，不是唯一性证明。

当前清单和 `data/raw/` 都是空的，直接运行会说明没有样本，并以退出码 0 结束。发现重复、字段错误或无法解码时退出码为 1。

## 不要做的事

不要把私人车牌照片或大型车牌数据集提交进这个仓库。小组后面如果使用自己拍摄或有许可的公开数据，在 `source` 里写明来源、许可和网址。没有许可的图不要放进来。
