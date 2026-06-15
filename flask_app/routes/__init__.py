"""路由注册模块。

Blueprint 总览：
- `auth_bp`       认证页面（/、/login、/register、/logout）
- `chat_bp`       聊天页面（/chat，需登录）
- `dashboard_bp`  用户仪表板（/dashboard，需 admin）
- `admin_bp`      管理页面（/admin，需 admin）
- `api_bp`        REST API（/api/*，Session 认证）
"""
from flask import Blueprint


def register_routes(app):
    """注册全部 Blueprint 到 Flask 应用。

    用法:
    - 调用方: `flask_app.create_app()` 应用工厂
    - `api_bp` 挂载前缀 `/api`，其余 Blueprint 无前缀
    """
    from . import admin, api, auth, chat, dashboard

    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(chat.chat_bp)
    app.register_blueprint(dashboard.dashboard_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(api.api_bp, url_prefix='/api')
