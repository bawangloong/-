"""生成全黑文字 PDF 阅读版。仅此工具需要 ReportLab，不是推理依赖。"""

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def pct(x):
    return f"{100 * x:.2f}%"


def create():
    pdfmetrics.registerFont(TTFont("CNSong", "C:/Windows/Fonts/simsun.ttc", subfontIndex=0))
    styles = {
        "title": ParagraphStyle("Title", fontName="CNSong", fontSize=24, leading=33, textColor=colors.black, spaceAfter=16),
        "subtitle": ParagraphStyle("Subtitle", fontName="CNSong", fontSize=13, leading=20, textColor=colors.black, spaceAfter=14),
        "h": ParagraphStyle("Heading", fontName="CNSong", fontSize=15, leading=22, textColor=colors.black, spaceBefore=12, spaceAfter=8),
        "p": ParagraphStyle("Body", fontName="CNSong", fontSize=10.5, leading=17, textColor=colors.black, spaceAfter=8, wordWrap="CJK"),
        "small": ParagraphStyle("Small", fontName="CNSong", fontSize=9, leading=14, textColor=colors.black, spaceAfter=6, wordWrap="CJK"),
        "code": ParagraphStyle("Code", fontName="CNSong", fontSize=9, leading=14, textColor=colors.black, spaceAfter=8, leftIndent=8, wordWrap="CJK"),
    }
    story = []

    def p(text, style="p"):
        story.append(Paragraph(escape(text).replace("\n", "<br/>"), styles[style]))

    def h(text):
        p(text, "h")

    def page(title):
        if story:
            story.append(PageBreak())
        p(title, "title")

    def table(rows, widths):
        data = [[Paragraph(escape(str(cell)), styles["small"]) for cell in row] for row in rows]
        t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.black),
                               ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                               ("TOPPADDING", (0, 0), (-1, -1), 5)]))
        story.append(t)
        story.append(Spacer(1, 9))

    def figure(path, width=485, max_height=330):
        absolute = ROOT / path
        w, h0 = ImageReader(str(absolute)).getSize()
        factor = min(width / w, max_height / h0)
        story.append(Image(str(absolute), w * factor, h0 * factor, hAlign="CENTER"))
        story.append(Spacer(1, 8))

    model = load("character_library/library.json")
    d = load("data_summary.json")
    t = load("results/test/metrics.json")
    val = load("results/validation/metrics.json")
    baseline = load("results/baseline_hog_test/metrics.json")
    real = load("results/real_library_test/metrics.json")
    b = load("results/B_integration/summary.json")
    a = t["unrestricted"]["all"]

    page("车牌识别 · C 部分")
    p("程序交付、使用说明、方法讲解与实验报告", "subtitle")
    p("交付日期：2026-11-16　｜　运行方式：CPU、离线识别", "small")
    h("你负责完成的部分")
    p("接收 B 按从左到右输出的字符切片，完成样本库匹配、逐字候选、相似度与复核提示，再拼接完整号码。已提供可独立运行的程序、字符库、评估和 B 联调示例。")
    table([["已交付", "对应文件 / 结果"],
           ["识别与构库", "recognize_chars.py、char_features.py、build_library.py、labels.py"],
           ["65 类字符库", f"library.npz：{model['samples']} 张模板，1348 维，包含归一化预览图"],
           ["B 实际联调", "integration_example.py、results/B_integration"],
           ["实验与失败分析", "evaluate_chars.py、results/test、对照结果、17 项检查"],
           ["中文材料", "使用说明、方法讲解、B/D 接口、C 部分报告、交付清单"]], [100, 385])
    h("当前结果")
    p(f"独立字符测试集 1,958 张，无类别约束 Top1 为 {pct(a['top1_accuracy'])}，Top3 为 {pct(a['top3_accuracy'])}。B 的五张正常合成车牌全部完整识别；倾斜样例只分出五字，返回数量异常。")
    h("交付边界")
    p("这份包完成 C 模块及 B 接口验证。A 的车辆检测与定位矫正、D 的 GUI 与 exe、E 的整体真实图验收和视频仍需小组继续完成。单字符指标与同字体合成图结果均不能替代真实整牌测试。")
    p("文字统一使用黑色。可编辑正文见同目录 Markdown 文件。", "small")

    page("1　运行与交付操作")
    h("当前电脑的最短运行路径")
    p("在 PowerShell 进入交付文件夹，使用已经验证的解释器：")
    p("Set-Location 'D:/课程文件/视频多媒体检索实践/车牌识别_C部分交付/plate_char_C'\n& 'D:/应用/python.exe' './integration_example.py'", "code")
    p("命令会重新调用 B 的颜色与分割，再进行 C 识别。打开 results/B_integration/summary.csv 看汇总，打开 *_matches.png 看每个字的 Top3。原始 B 交付位于 integration/B_original，内容未修改。")
    h("只识别 B 已保存的切片")
    p("& 'D:/应用/python.exe' './recognize_chars.py' --chars-dir './integration/B_original/output/blue_7_chars' --output './results/local_blue.json' --visualize './results/local_blue.png'", "code")
    p("字符按自然文件名顺序读取。文件夹仅放同一块车牌的切片，不能混入整牌图、过程图或其他车牌。")
    h("换机使用独立 Python 环境")
    p("py -3.13 -m venv .venv\n& './.venv/Scripts/python.exe' -m pip install -r requirements.txt\n& './.venv/Scripts/python.exe' './integration_example.py'", "code")
    p("若本机没有 3.13，可换为已安装 Python 的完整路径。运行依赖仅 NumPy、OpenCV、Pillow，安装需要联网，识别时可离线。无需 GPU、PyTorch 或神经网络训练。其他版本组合未逐一验证。")
    h("接收真实新图与重新构库")
    p("新的输入必须是 A 已裁切并矫正的单块车牌；用 integration_example.py --image '图片路径' --output './results/local_real' 调用。外部图不自动填写真值。")
    p("添加人工确认的训练字符到 character_library/train/<标签>/，用 build_library.py --output './character_library/library_custom.npz' 另存新库。不要把测试图或 B 的测试切片直接加入训练。")
    p("完整命令、单字符识别、常见错误与重新评估见 README_使用说明.md。", "small")

    page("2　给 B 与 D 的调用接口")
    h("直接接 B 的返回值")
    p("from recognize_chars import CharacterRecognizer\nfrom integration_example import recognize_b_result\nrecognizer = CharacterRecognizer()\nc_result = recognize_b_result(b_result, recognizer)\ntext = c_result['text']\nrows = c_result['characters']", "code")
    p("recognizer 初始化一次并复用。b_result['chars'] 应为 list/tuple，按阅读顺序；count 必须与实际切片数量一致。B 的 40×20 灰度白字黑底 uint8 数组可直接使用。")
    h("图像和坐标约定")
    p("C 接灰度、BGR、BGRA 数组或中文图片路径。支持 uint8 0-255、bool、0/1 uint8、有限 [0,1] 浮点。BToC.run 的完整彩色入口则接 RGB；A 若用 cv2，须先 BGR 转 RGB。")
    p("B 文档对 boxes 坐标存在冲突，实际代码返回高度归一化到 140 的 norm 图坐标。D 不能直接在原尺寸图上使用这些框，应按尺寸换算。")
    table([["C 状态", "上层展示 / 处理"],
           ["ok", "展示号码；仍不保证每字正确"], ["needs_review", "展示号码并提示复核，保留 Top3"],
           ["no_characters", "提示未分出字符"], ["invalid_length", "切片非 7/8 张，text 为空；检查分割与矫正"],
           ["partial_failure", "坏字符以 ? 保留原位置"], ["单字 invalid_input", "提示 message，检查空白图或像素范围"]], [115, 370])
    h("候选、线程和资源")
    p("每字包含 position（从 0 开始）、label、similarity、margin、status、message、candidates。候选含 label、similarity、sample_index、sample_path。可用 recognizer.normalized_images[sample_index] 直接显示最佳模板。")
    p("npz 必须随 exe 打包，或显式传入 CharacterRecognizer(实际资源路径)。GUI 建议在工作线程推理，避免反复加载约 10 MB 的库。C 未代替 D 生成完整 exe，最终须在无 Python 电脑验证。")

    page("3　算法如何完成识别")
    h("预处理：先把比较对象对齐")
    p("灰度化 → Otsu → 边界多数投票判断背景 → 白字黑底 → 裁全部前景框 → 保持比例将最长边缩放到 28 → 放入 32×32 画布。汉字保留分离笔画，不能只保留最大连通域。")
    h("HOG：记录笔画边缘的方向")
    p("gx=f(x+1,y)-f(x-1,y)；gy=f(x,y+1)-f(x,y-1)\n幅值=sqrt(gx²+gy²)；无符号方向=atan2(gy,gx) mod pi", "code")
    p("32×32 分成 4×4 个 8×8 cell，每个 cell 有 9 个方向 bin。像素按梯度幅值向相邻两个方向 bin 线性投票，不做 cell 间空间投票。2×2 cell 构成 block，步长一个 cell，共 3×3 block。")
    p("HOG 维数 = 3×3×2×2×9 = 324。每个 block 使用 L2-Hys：L2 归一化、截断至 0.2、再 L2。拼接后做 L1、平方根、L2，得到单位向量 h。该 HOG 使用 NumPy 明确实现。")
    h("像素：补充笔画的精确位置")
    p("32×32 图展平为 1024 维并归一化，记为 p。组合特征和相似度为：")
    p("z = concat(sqrt(0.55)·h, sqrt(0.45)·p)\ndim(z) = 324+1024 = 1348，且 ||z||=1\nS(q,s) = zq·zs = 0.55·cos(hq,hs)+0.45·cos(pq,ps)", "code")
    h("分类与复核")
    p("每类取最相似样本：score(c)=max S(q,s)，再输出得分最大的类别。Top3 对应三个不同类别，并提供其实际样本路径。standard 模式限制首位省份、第二位字母、其余数字/字母。")
    p("margin 为前两种类别的分差；相似度<0.75 或 margin<0.02 时建议复核。这是启发式提示，分数不是正确概率。位置约束没有完整检查全部新能源与特殊号牌规则。")

    page("4　数据、参数与字符评估")
    p(f"公开样本来源于 wzh191920/License-Plate-Recognition 固定提交 {d['commit']} 的两个字符压缩包；上游注明来源为 EasyPR。来源、许可、哈希和排除明细均已保存。", "small")
    table([["数据处理", "数量 / 设置"], ["公开原始图片", d['raw_supported_images']],
           ["同归一化图去重 / 标签冲突排除", "3334 / 15"], ["保留公开独立图", d['kept_images']],
           ["train / validation / test", "9130 / 1958 / 1958；随机种子 20261116"],
           ["辅助字体模板", "387 张，65 类，微软雅黑/黑体，48/64/80 字号"],
           ["最终训练模板", model['samples']]], [220, 265])
    p("去重先于分层划分。字体模板对全部类别统一独立生成，不读取 B 切片或号码；字体文件未分发。支持 10 数字、24 字母（无 I/O）及 31 省份汉字；zh_qing 输出规范‘青’。")
    p("验证集比较像素权重 0/0.15/0.30/0.45/0.60，Top1 依次为 91.73/95.61/96.78/96.88/96.53%，固定 0.45。首次基线测试结果已在开发中查看，因此当前测试属于开发留出集，仍需额外盲测。")
    table([["方案", "测试 Top1"], ["纯 HOG / 公开训练", pct(baseline['unrestricted']['all']['top1_accuracy'])],
           ["HOG+像素 / 公开训练", pct(real['unrestricted']['all']['top1_accuracy'])],
           ["HOG+像素 / 加字体模板", pct(a['top1_accuracy'])]], [355, 130])
    rows = [["最终测试类别", "数量", "Top1", "Top3"]]
    for name, key in [("全部", "all"), ("数字", "digits"), ("字母", "letters"), ("省份汉字", "provinces")]:
        m = t['unrestricted'][key]
        rows.append([name, m['count'], pct(m['top1_accuracy']), pct(m['top3_accuracy'])])
    table(rows, [180, 75, 115, 115])
    p(f"宏平均召回率 {pct(a['macro_recall'])}。在已知‘省份/字母数字’类型约束下 Top1 为 {pct(t['type_constrained']['all']['top1_accuracy'])}。原始 CSV、混淆矩阵和失败图见 results/test。", "small")
    p("同源随机划分不能排除近重复或共同原始车牌。藏仅有 1 张测试图，稀有类百分比很不稳定。以上是单字符结果，不是整牌准确率。", "small")

    page("5　B 联调、失败与验证")
    p("实际重新调用 B 颜色与分割函数，六组输出与 B 原存档逐像素一致。补充字体前仅 1/6 完整识别；补充后五张分割正常图全部完整识别，倾斜图保持异常。")
    rows = [["B 样例", "真值 / 输出", "切片数", "结果"]]
    for row in b['rows']:
        rows.append([row['file'], row['truth'] + " / " + (row['prediction'] or "无号码"), row['count'], "一致" if row['exact_match'] else "数量异常"])
    table(rows, [110, 240, 60, 75])
    p("B 样例是合成图，并与辅助模板使用相同字体家族，所以结果主要验证接口与同字体兼容；不能称为真实道路、跨字体泛化。未把 B 的测试切片加入训练。")
    h("独立字符集仍有错误")
    figure("results/test/failure_cases.png", max_height=190)
    p("常见问题包括 D/0、7/T、B/M 的同形混淆、汉字低分辨率、裁切和断笔。即使 status=ok 也有误识别；复核提示和 Top3 仅提供依据。分割数量正确也不意味着每张切片完整。", "small")
    h("完成的验证")
    p("17 项行为检查通过：中文路径、极性与数据格式、纯色等坏输入、7/8 位、坏字保留位置、Top3 类别区分、float64 欧氏距离独立核对、全量图像哈希及划分隔离、构库去重与冲突、B 像素复现、CLI 失败退出码。")
    p("最终 ZIP 还进行解压后离线识别、重新构库和结果一致性验收，记录见 acceptance_record.json。尚未进行未参与开发的真实整牌盲测，也未验证完整 exe。", "small")

    page("6　交接、讲解与后续")
    h("各成员拿走哪些内容")
    table([["成员", "C 提供的交接物"], ["B", "接口说明、实际分割复现、五张正常样例结果、倾斜异常；确认 RGB 与灰度约定及框坐标"],
           ["D", "核心 .py、library.npz、适配器和返回状态；将资源加入 GUI/exe，工作线程复用识别器"],
           ["E", "C 部分报告、指标 CSV/JSON、失败图、对照结果、来源许可、检查及解压验收记录"],
           ["自己", "使用说明、方法讲解、可运行示例、构库与评估脚本；下述口头讲解可直接调整使用"]], [65, 420])
    h("口头讲解参考")
    p("我负责字符样本库和字符识别。B 给出有序的 40×20 灰度切片，我先统一前景、裁边并居中到 32×32。然后提取 324 维 HOG 和 1024 维像素特征，使用验证集选定的权重拼接。查询与库中样本做余弦匹配，每个类别保留最像的样本，输出不同类别 Top3，再施加常见位置约束。候选接近时提示复核，坏切片保留问号，数量异常交回上游检查。我分别评估了独立字符集和 B 的合成样例，两者代表不同能力，完整系统还需要真实整牌测试。")
    h("系统验收时优先补齐")
    p("让 A/B 提供新的真实图和逐字标注；覆盖不同字体、光照、模糊、倾斜与多个车牌。先固定这份 C 基线，再比较错误来自检测、分割还是匹配，避免根据测试答案修规则。特殊字符需新增标签、训练数据和布局。D/E 应在另一台无 Python Windows 电脑运行最终 exe。")
    h("环境和来源")
    p("本次使用 Windows 11、Python 3.13.7、NumPy 2.3.5、OpenCV 5.0.0、Pillow 12.0.0；PDF 由已有 ReportLab 5.0.1 生成，没有安装新依赖。完整版本与来源见 Markdown 文档。", "small")
    p("公开数据：github.com/wzh191920/License-Plate-Recognition\n原始来源说明：github.com/liuruoze/EasyPR\nB：用户提供的 B模块_颜色识别与字符分割.zip，原样保留。", "small")
    p("运行依赖见 requirements.txt；此 PDF 生成工具不属于核心推理依赖。", "small")

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.black)
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(0.4)
        canvas.line(48, 39, 547, 39)
        canvas.setFont("CNSong", 8)
        canvas.drawString(48, 25, "车牌识别 C 部分 | 使用、方法与实验 | 2026-11-16")
        canvas.drawRightString(547, 25, str(doc.page))
        canvas.restoreState()

    output = ROOT / "C部分说明与报告.pdf"
    SimpleDocTemplate(str(output), pagesize=(595.28, 841.89), leftMargin=55, rightMargin=55,
                      topMargin=45, bottomMargin=53, title="车牌识别 C 部分说明与报告", author="课程项目 C 模块").build(
                          story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == "__main__":
    create()
