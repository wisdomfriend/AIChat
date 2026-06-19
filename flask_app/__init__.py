"""Flask 应用工厂。

启动流程（按初始化顺序）：
1) 创建 Flask 实例并加载配置
2) 初始化 Redis 连接（限流使用；失败则限流降级放行）
3) `register_request_logging()`  注册请求日志
4) `init_db()`  确保数据库连接可用
5) `register_error_handlers()` / `register_cors()`  统一异常与跨域
6) 注册静态文件哈希处理与全部路由
7) 初始化 Swagger API 文档（/api-docs）
"""
import logging

from flask import Flask, request
from flasgger import Swagger
import redis

from .config import create_config
from .database import init_db
from .middleware import register_cors, register_error_handlers, register_request_logging
from .routes import register_routes
from .utils import get_static_file_hash

logger = logging.getLogger(__name__)


def create_app(config_name='default'):
    """创建并配置 Flask 应用实例。

    用法:
    - 调用方: `run.py`、`wsgi.py`
    - 参数: `config_name`  配置名称（development / production 等）
    - 返回值: 已完成 Redis、数据库、路由与 Swagger 注册的 Flask app
    """
    app = Flask(__name__)
    
    # 使用配置工厂函数创建配置实例（此时环境变量已经加载）
    config_instance = create_config(config_name)
    app.config.from_object(config_instance)
    
    # 初始化 Redis 连接（仅用于聊天限流；认证已改为 Bearer Token，不再使用 Redis Session）
    try:
        redis_client = redis.Redis(
            host=config_instance.REDIS_HOST,
            port=config_instance.REDIS_PORT,
            db=config_instance.REDIS_DB,
            password=config_instance.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        redis_client.ping()
        app.config['REDIS_CLIENT'] = redis_client
        logger.info(f"Redis连接成功: {config_instance.REDIS_HOST}:{config_instance.REDIS_PORT}")
    except Exception as e:
        logger.error(f"Redis连接失败: {str(e)}", exc_info=True)
        logger.warning("限流将降级为放行模式")
        app.config['REDIS_CLIENT'] = None
    
    register_request_logging(app)

    # 初始化数据库
    try:
        init_db()
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}", exc_info=True)
        # 不抛出异常，允许应用启动，但会在实际使用时失败

    register_error_handlers(app)
    register_cors(app)
    
    # 注册模板过滤器：用于生成带哈希的静态文件URL
    @app.template_filter('static_hash')
    def static_hash_filter(filename):
        """模板过滤器：为静态文件添加哈希值"""
        hashed_filename = get_static_file_hash(filename)
        # 直接返回带哈希的文件路径
        return f"/static/{hashed_filename}"
    
    # 使用 before_request 拦截静态文件请求，处理带哈希的文件
    @app.before_request
    def handle_hashed_static():
        """拦截并处理带哈希的静态文件请求"""
        import os
        import re
        from flask import request, send_from_directory, abort, current_app
        
        # 只处理 /static/ 路径的请求
        if not request.path.startswith('/static/'):
            return None
        
        # 提取文件路径（去掉 /static/ 前缀）
        file_path = request.path[8:]  # 去掉 '/static/' (8个字符)
        
        # 检查是否是带哈希的文件名格式：path/to/file.hash.ext
        pattern = r'^(.+)\.([a-f0-9]{8})(\.[^.]+)$'
        match = re.match(pattern, file_path)
        
        if match:
            # 找到匹配，提取原始文件名
            base_path = match.group(1)
            file_ext = match.group(3)
            original_filename = base_path + file_ext
            
            # 验证哈希值是否正确
            expected_hashed = get_static_file_hash(original_filename)
            if file_path == expected_hashed:
                # 哈希值匹配，返回原始文件
                return send_from_directory(current_app.static_folder, original_filename)
            else:
                # 哈希值不匹配，可能是旧缓存，返回404
                logger.warning(f"静态文件哈希不匹配: 请求={file_path}, 期望={expected_hashed}")
                abort(404)
        
        # 不是带哈希的文件，继续默认处理流程
        return None
    
    # 注册路由（必须在静态文件路由之后）
    register_routes(app)
    
    # 初始化 Swagger 文档
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
            - 除公开接口外，API 需 Bearer Token 认证
            - 请求头: `Authorization: Bearer <token>`
            - 登录获取 token: `POST /api/auth/login`
            - Swagger 中点击 Authorize，输入: `Bearer <token>`
            """,
            "version": "1.0.0",
            "contact": {
                "email": "wisdomfriend@126.com"
            }
        },
        "basePath": "/api",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "bearerAuth": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "Bearer Token 认证，格式: Bearer <token>（先调用 POST /api/auth/login 获取）",
            },
            "sessionAuth": {
                "type": "apiKey",
                "name": "Cookie",
                "in": "header",
                "description": "（已废弃）旧版 Session Cookie 认证，请改用 bearerAuth",
            },
        },
        "tags": [
            {
                "name": "认证",
                "description": "Bearer Token 登录、注册与用户信息",
            },
            {
                "name": "系统",
                "description": "健康检查与服务探活",
            },
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
            },
            {
                "name": "统计",
                "description": "Token 用量统计（用户/管理员）"
            }
        ]
    }
    
    Swagger(app, config=swagger_config, template=swagger_template)
    logger.info("Swagger 文档已初始化，访问 /api-docs 查看 API 文档")
    
    return app
