"""路由注册模块。

Blueprint 总览：
- `health_bp`    健康检查（/health）
- `auth_bp`       旧版认证页面（迁移过渡期保留）
- `auth_api_bp`   Bearer Token 认证 API（/api/auth/*）
- `chat_bp`       聊天页面（/chat，需登录）
- `dashboard_bp`  用户仪表板（/dashboard，需 admin）
- `admin_bp`      管理页面（/admin，需 admin）
- `api_bp`        REST API（/api/*，Bearer 认证）
"""
from flask import Blueprint


def register_routes(app):
    """注册全部 Blueprint 到 Flask 应用。

    用法:
    - 调用方: `flask_app.create_app()` 应用工厂
    - 挂载前缀: `/api`（`api_bp`）、`/api/auth`（`auth_api_bp`）
    - 其余 Blueprint 无前缀
    """
    from . import admin, api, auth, auth_api, chat, dashboard, health

    app.register_blueprint(health.health_bp)
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(chat.chat_bp)
    app.register_blueprint(dashboard.dashboard_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(api.api_bp, url_prefix='/api')
    app.register_blueprint(auth_api.auth_api_bp, url_prefix='/api/auth')
