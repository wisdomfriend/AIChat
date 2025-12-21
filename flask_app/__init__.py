"""Flask应用工厂"""
import logging
from flask import Flask, request
from flask_cors import CORS
from flasgger import Swagger
import redis
from .config import create_config
from .database import init_db
from .routes import register_routes
from .session_interface import FixedRedisSessionInterface

logger = logging.getLogger(__name__)


def create_app(config_name='default'):
    """创建Flask应用实例"""
    app = Flask(__name__)
    
    # 使用配置工厂函数创建配置实例（此时环境变量已经加载）
    config_instance = create_config(config_name)
    app.config.from_object(config_instance)
    
    # 初始化Redis连接（用于Session存储）
    try:
        # 注意：不能使用 decode_responses=True，因为 Flask-Session 使用 pickle 序列化二进制数据
        redis_client = redis.Redis(
            host=config_instance.REDIS_HOST,
            port=config_instance.REDIS_PORT,
            db=config_instance.REDIS_DB,
            password=config_instance.REDIS_PASSWORD,
            decode_responses=False,  # 必须为 False，因为 Session 数据是二进制格式
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # 测试Redis连接
        redis_client.ping()
        app.config['SESSION_REDIS'] = redis_client
        logger.info(f"Redis连接成功: {config_instance.REDIS_HOST}:{config_instance.REDIS_PORT}")
    except Exception as e:
        logger.error(f"Redis连接失败: {str(e)}", exc_info=True)
        logger.warning("将回退到默认的Cookie Session存储")
        # 如果Redis连接失败，回退到默认的Cookie Session
        app.config['SESSION_TYPE'] = 'filesystem'
        app.config['SESSION_REDIS'] = None
    
    # 配置Flask-Session - 使用自定义接口修复session_id bytes问题
    if app.config.get('SESSION_REDIS'):
        # 如果Redis连接成功，使用自定义的Redis Session接口
        # 设置 SameSite=None 以便 Swagger UI 能够发送 Cookie（开发环境）
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # 同域请求时允许发送 Cookie
        # 确保 SESSION_COOKIE_NAME 已设置（Flask 默认是 'session'）
        if 'SESSION_COOKIE_NAME' not in app.config:
            app.config['SESSION_COOKIE_NAME'] = 'session'
        app.session_interface = FixedRedisSessionInterface(
            redis=app.config['SESSION_REDIS'],
            key_prefix=app.config.get('SESSION_KEY_PREFIX', 'session:'),
            use_signer=app.config.get('SESSION_USE_SIGNER', True),
            permanent=app.config.get('SESSION_PERMANENT', True)
        )
        logger.info(f"使用自定义Redis Session接口，Cookie名称: {app.config['SESSION_COOKIE_NAME']}")
    else:
        # 如果Redis连接失败，使用默认的文件系统Session
        from flask_session import Session
        Session(app)
        logger.info("使用默认文件系统Session")
    
    # 初始化数据库
    try:
        init_db()
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
        # 不抛出异常，允许应用启动，但会在实际使用时失败
    
    # 注册路由
    register_routes(app)
    
    # 初始化 Swagger 文档
    # 注意：不设置 host 字段，让 Swagger UI 使用相对路径（自动使用当前页面的 host）
    # 这样无论通过什么域名访问，都能正确工作，无需处理跨域问题
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api-docs"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "AIChat API 文档",
            "description": """
            AI 聊天应用的 API 接口文档，支持聊天、文件管理、会话管理等功能。
            
            **重要提示：**
            - 所有 API 接口都需要用户登录认证
            - 请在浏览器中先访问登录页面（/login）完成登录
            - 登录后，浏览器的 Cookie 会自动发送到 API 请求中
            - 如果遇到 401 未登录错误，请先登录系统，然后刷新此页面
            """,
            "version": "1.0.0",
            "contact": {
                "email": "wisdomfriend@126.com"
            }
        },
        # 不设置 host，让 Swagger UI 使用相对路径（自动使用当前页面的 host）
        # 这样无论通过 127.0.0.1:5000 还是 guopengfei.top 访问，都能正确工作
        "basePath": "/api",
        "schemes": ["http", "https"],  # 支持两种协议
        "tags": [
            {
                "name": "聊天",
                "description": "AI 聊天相关接口"
            },
            {
                "name": "会话",
                "description": "会话管理相关接口"
            },
            {
                "name": "文件",
                "description": "文件上传和管理相关接口"
            },
            {
                "name": "模型",
                "description": "LLM 模型提供商相关接口"
            }
        ]
    }
    
    # 初始化 Swagger
    # 注意：Flasgger 0.9.7.1 版本可能存在将 Python None 输出到 JavaScript 的问题
    # 这是已知问题，不影响功能，但会在浏览器控制台显示错误
    Swagger(app, config=swagger_config, template=swagger_template)
    logger.info("Swagger 文档已初始化，访问 /api-docs 查看 API 文档")
    
    return app

