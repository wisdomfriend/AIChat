"""路由注册模块。

Blueprint 总览：
- `health_bp`    健康检查（/health）
- `auth_bp`      Bearer Token 认证 API（/api/auth/*）
- `auth_debug_bp` 认证调试（/api/test-auth）
- `chat_bp`      聊天与会话 API（/api/chat、/api/sessions/*）
- `file_bp`      文件管理 API（/api/files/*）
- `llm_bp`       LLM 模型 API（/api/llm/*）
- `stats_api_bp` Token 统计 API（/api/stats/*）
"""


def register_routes(app):
    """注册全部 Blueprint 到 Flask 应用。"""
    from . import auth, chat, file, health, llm, stats_api

    app.register_blueprint(health.health_bp)
    app.register_blueprint(auth.auth_bp, url_prefix="/api/auth")
    app.register_blueprint(auth.auth_debug_bp, url_prefix="/api")
    app.register_blueprint(chat.chat_bp, url_prefix="/api")
    app.register_blueprint(file.file_bp, url_prefix="/api")
    app.register_blueprint(llm.llm_bp, url_prefix="/api")
    app.register_blueprint(stats_api.stats_api_bp, url_prefix="/api/stats")
