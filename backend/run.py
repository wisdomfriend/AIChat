#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发环境启动入口。

用法:
- 命令: `python backend/run.py`（在项目根目录执行）
- 行为: 加载 `backend/.env.develop` → `create_app(mode=DEVELOP)` → 启动内置开发服务器
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from backend import create_app
from backend.config import DEVELOP

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(BACKEND_DIR / ".env.develop")

app = create_app(mode=DEVELOP)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug="1", use_reloader=False)
