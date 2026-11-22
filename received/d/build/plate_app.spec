# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（D 模块）。

用法：pyinstaller build/plate_app.spec --noconfirm --clean
生成 dist/车牌识别系统/ 单目录发行包。
"""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent.parent

datas = [
    # C 的字符库：运行期由 app/runtime.py 通过 sys._MEIPASS 定位
    (str(ROOT / "vendor" / "c_char" / "character_library"),
     "vendor/c_char/character_library"),
    # 演示图片与文档（可选，方便老师和同学直接试）
    (str(ROOT / "samples"), "samples"),
    (str(ROOT / "docs"), "docs"),
    (str(ROOT / "README.md"), "."),
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=["PIL._tkinter_finder"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "pytest", "docx", "pptx", "lxml"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="车牌识别系统",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="车牌识别系统",
)
