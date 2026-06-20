"""nginx-shop 后端包。

对外入口：
- `create_app`  Flask 应用工厂，供 WSGI 或开发服务器启动
"""
from backend.app import create_app

__all__ = ["create_app"]
