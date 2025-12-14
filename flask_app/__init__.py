"""Flask应用工厂"""
import logging
from flask import Flask
from flask_cors import CORS
from .config import create_config
from .database import init_db
from .routes import register_routes

logger = logging.getLogger(__name__)


def create_app(config_name='default'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 使用配置工厂函数创建配置实例（此时环境变量已经加载）
    config_instance = create_config(config_name)
    app.config.from_object(config_instance)
    
    # 启用CORS
    CORS(app)
    
    # 初始化数据库
    try:
        init_db()
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
        # 不抛出异常，允许应用启动，但会在实际使用时失败
    
    # 注册路由
    register_routes(app)
    
    return app

