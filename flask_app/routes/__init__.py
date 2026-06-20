"""路由注册模块。

Blueprint 总览：
- `health_bp`     健康检查（/health）
- `auth_api_bp`   Bearer Token 认证 API（/api/auth/*）
- `api_bp`        REST API（/api/*，Bearer 认证）
- `stats_api_bp`  Token 统计 API（/api/stats/*）
"""
from flask import Blueprint


def register_routes(app):
    """注册全部 Blueprint 到 Flask 应用。

    用法:
    - 调用方: `flask_app.create_app()` 应用工厂
    - 挂载前缀: `/api`（`api_bp`）、`/api/auth`（`auth_api_bp`）、`/api/stats`（`stats_api_bp`）
    """
    from . import api, auth_api, health, stats_api

    app.register_blueprint(health.health_bp)
    app.register_blueprint(api.api_bp, url_prefix='/api')
    app.register_blueprint(auth_api.auth_api_bp, url_prefix='/api/auth')
    app.register_blueprint(stats_api.stats_api_bp, url_prefix='/api/stats')
