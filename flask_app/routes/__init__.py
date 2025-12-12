"""路由模块"""
from flask import Blueprint


def register_routes(app):
    """注册所有路由到应用"""
    # 导入路由模块（延迟导入避免循环依赖）
    from . import auth, chat, dashboard, admin, api
    
    # 注册蓝图
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(chat.chat_bp)
    app.register_blueprint(dashboard.dashboard_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(api.api_bp, url_prefix='/api')

