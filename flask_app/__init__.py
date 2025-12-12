"""Flask应用工厂"""
from flask import Flask
from flask_cors import CORS
from .config import config
from .database import init_db
from .routes import register_routes


def create_app(config_name='default'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 启用CORS
    CORS(app)
    
    # 初始化数据库
    init_db()
    
    # 注册路由
    register_routes(app)
    
    return app

