# -*- coding: utf-8 -*-
"""绿色发行包入口：任何启动异常都写日志并弹窗，避免 windowed 模式静默退出。"""

from __future__ import annotations

import ctypes
import sys
import time
import traceback
from pathlib import Path

BASE = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent


def fatal(message: str) -> None:
    log_dir = BASE / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "startup_error.log").write_text(message, encoding="utf-8")
    except OSError:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(0, message[-1800:], "车牌识别系统 启动失败", 0x10)
    except Exception:
        print(message, file=sys.stderr)


if __name__ == "__main__":
    try:
        sys.path.insert(0, str(BASE))
        from app.main import main
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        fatal("启动失败：\n\n" + traceback.format_exc())
        raise SystemExit(1)
