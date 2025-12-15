"""Flask应用工厂"""
import logging
from flask import Flask
from flask_cors import CORS
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
        app.session_interface = FixedRedisSessionInterface(
            redis=app.config['SESSION_REDIS'],
            key_prefix=app.config.get('SESSION_KEY_PREFIX', 'session:'),
            use_signer=app.config.get('SESSION_USE_SIGNER', True),
            permanent=app.config.get('SESSION_PERMANENT', True)
        )
        logger.info("使用自定义Redis Session接口")
    else:
        # 如果Redis连接失败，使用默认的文件系统Session
        from flask_session import Session
        Session(app)
        logger.info("使用默认文件系统Session")
    
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

