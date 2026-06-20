#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WSGI 生产环境入口。

用法:
- 部署: gunicorn 等通过 `backend.wsgi:app` 加载
- 行为: 加载 `backend/.env.product` → `create_app(mode=PRODUCT)` → 创建 Flask 应用实例
- Docker: compose 已注入 environment 时，以容器环境变量为准（load_dotenv 不覆盖已有变量）
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from backend import create_app
from backend.config import PRODUCT

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(BACKEND_DIR / ".env.product")

app = create_app(mode=PRODUCT)
