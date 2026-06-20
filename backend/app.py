"""Flask 应用工厂。

启动流程（按初始化顺序）：
1) 创建 Flask 实例并加载配置
2) 初始化 Redis 连接（限流使用；失败则限流降级放行）
3) `register_request_logging()`  注册请求日志
4) `init_db()`  确保数据库连接可用
5) `register_error_handlers()` / `register_cors()`  统一异常与跨域
6) 注册全部 API 路由
7) 初始化 Swagger API 文档（/api-docs）
"""
import logging

from flask import Flask
from flasgger import Swagger
import redis

from backend.config import APP_CONFIG_KEY, configure_app
from backend.db import init_db
from backend.middleware import register_cors, register_error_handlers, register_request_logging
from backend.routes import register_routes

logger = logging.getLogger(__name__)


def create_app(config_name="default"):
    """创建并配置 Flask 应用实例。"""
    app = Flask(__name__)

    configure_app(app, config_name=config_name)
    config_instance = app.extensions[APP_CONFIG_KEY]

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
        app.config["REDIS_CLIENT"] = redis_client
        logger.info("Redis连接成功: %s:%s", config_instance.REDIS_HOST, config_instance.REDIS_PORT)
    except Exception as e:
        logger.error("Redis连接失败: %s", e, exc_info=True)
        logger.warning("限流将降级为放行模式")
        app.config["REDIS_CLIENT"] = None

    register_request_logging(app)

    try:
        init_db()
    except Exception as e:
        logger.error("数据库初始化失败: %s", e, exc_info=True)

    try:
        from backend.services.checkpointer_service import init_checkpointer

        init_checkpointer(config_instance)
    except Exception as e:
        logger.error("Postgres checkpointer 初始化失败: %s", e, exc_info=True)
        logger.warning("Agent 对话功能可能不可用，请检查 PostgreSQL 配置")

    register_error_handlers(app)
    register_cors(app)

    register_routes(app)

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
        "specs_route": "/api-docs",
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
                "email": "wisdomfriend@126.com",
            },
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
        },
        "tags": [
            {"name": "认证", "description": "Bearer Token 登录、注册与用户信息"},
            {"name": "系统", "description": "健康检查与服务探活"},
            {"name": "聊天", "description": "AI 聊天相关接口"},
            {"name": "会话", "description": "会话管理相关接口"},
            {"name": "文件", "description": "文件上传和管理相关接口"},
            {"name": "模型", "description": "LLM 模型提供商相关接口"},
            {"name": "统计", "description": "Token 用量统计（用户/管理员）"},
        ],
    }

    Swagger(app, config=swagger_config, template=swagger_template)
    logger.info("Swagger 文档已初始化，访问 /api-docs 查看 API 文档")

    return app
