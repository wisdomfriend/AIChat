"""按运行环境创建应用配置对象。"""
import logging
import os
from pathlib import Path

from backend.config.settings import (
    ALLOWED_EXTENSIONS,
    DEEPSEEK_API_URL,
    DEFAULT_LOG_DIR,
    IMAGE_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_FILES_PER_REQUEST,
    MAX_TEXT_LENGTH,
)

logger = logging.getLogger(__name__)

DEVELOP = "development"
PRODUCT = "production"


def allowed_origins() -> list[str]:
    """读取 CORS 允许的前端来源列表。"""
    configured = os.environ.get(
        "CORS_ALLOW_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    return [item.strip() for item in configured.split(",") if item.strip()]


def resolve_log_dir() -> Path:
    """解析应用日志存储目录。"""
    env_dir = os.environ.get("LOG_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return DEFAULT_LOG_DIR


class Config:
    """基础配置，实例化时从环境变量加载全部运行时参数。"""

    DEEPSEEK_API_URL = DEEPSEEK_API_URL
    MAX_FILE_SIZE = MAX_FILE_SIZE
    MAX_FILES_PER_REQUEST = MAX_FILES_PER_REQUEST
    MAX_TEXT_LENGTH = MAX_TEXT_LENGTH
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    IMAGE_EXTENSIONS = IMAGE_EXTENSIONS

    def __init__(self):
        self.SECRET_KEY = os.environ.get("SECRET_KEY", "guopengfei")

        self.MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql")
        self.MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "23306"))
        self.MYSQL_USER = os.environ.get("MYSQL_USER", "guopengfei")
        self.MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "guopengfei")
        self.MYSQL_DB = os.environ.get("MYSQL_DB", "backend")

        self.REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
        self.REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
        self.REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
        redis_password = os.environ.get("REDIS_PASSWORD", None)
        if redis_password in (None, "", "None", "null", "NULL"):
            self.REDIS_PASSWORD = None
        else:
            self.REDIS_PASSWORD = redis_password
        self.REDIS_CLIENT = None

        self.AUTH_TOKEN_SECRET = os.environ.get("AUTH_TOKEN_SECRET", self.SECRET_KEY)
        self.AUTH_TOKEN_MAX_AGE = int(os.environ.get("AUTH_TOKEN_MAX_AGE", "86400"))

        self.FLASK_ENV = os.environ.get("FLASK_ENV", "development")

        self.POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
        self.POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER = os.environ.get("POSTGRES_USER", "langgraph")
        self.POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "langgraph")
        self.POSTGRES_DB = os.environ.get("POSTGRES_DB", "langgraph")

        self.AGENT_SUMMARY_TRIGGER_FRACTION = float(
            os.environ.get("AGENT_SUMMARY_TRIGGER_FRACTION", "0.8")
        )
        self.AGENT_SUMMARY_KEEP_MESSAGES = int(
            os.environ.get("AGENT_SUMMARY_KEEP_MESSAGES", "20")
        )
        self.AGENT_RECURSION_LIMIT = int(os.environ.get("AGENT_RECURSION_LIMIT", "25"))

        self._init_llm_providers()
        self._init_web_search_config()
        self._validate_config()

    def _init_llm_providers(self):
        self.DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
        self.LLM_PROVIDERS = {
            "deepseek": {
                "type": "openai_compatible",
                "base_url": "https://api.deepseek.com/v1",
                "api_key": self.DEEPSEEK_API_KEY,
                "model_name": "deepseek-v4-flash",
                "display_name": "deepseek-v4-flash",
                "max_context_length": 512000,
                "supports_images": False,
                "enabled": True,
            },
        }
        self.LLM_DEFAULT_PROVIDER = "deepseek"

    def _init_web_search_config(self):
        self.TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
        self.TAVILY_SEARCH_MAX_RESULTS = int(os.environ.get("TAVILY_SEARCH_MAX_RESULTS", "3"))
        self.BAIDU_SEARCH_MAX_RESULTS = int(os.environ.get("BAIDU_SEARCH_MAX_RESULTS", "3"))

    def _validate_config(self):
        if self.FLASK_ENV == "production":
            if not os.environ.get("MYSQL_HOST"):
                logger.warning("警告: 生产环境中未设置 MYSQL_HOST 环境变量，使用默认值 'mysql'")
            if not os.environ.get("MYSQL_USER"):
                logger.warning("警告: 生产环境中未设置 MYSQL_USER 环境变量，使用默认值")
            if not os.environ.get("MYSQL_PASSWORD"):
                logger.warning("警告: 生产环境中未设置 MYSQL_PASSWORD 环境变量，使用默认值")
            if not os.environ.get("MYSQL_DB"):
                logger.warning("警告: 生产环境中未设置 MYSQL_DB 环境变量，使用默认值")

    @property
    def DATABASE_URL(self):
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        )

    @property
    def POSTGRES_URI(self):
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class DevelopmentConfig(Config):
    def __init__(self):
        super().__init__()
        self.DEBUG = True


class ProductionConfig(Config):
    def __init__(self):
        super().__init__()
        self.DEBUG = False


def create_config(*, mode: str = DEVELOP):
    """从已加载的环境变量创建配置对象。"""
    if mode not in (DEVELOP, PRODUCT, "development", "production", "default"):
        raise RuntimeError(
            f"不支持的运行模式: {mode!r}，仅允许 {DEVELOP!r} 或 {PRODUCT!r}"
        )
    config_map = {
        "development": DevelopmentConfig,
        "production": ProductionConfig,
        "default": DevelopmentConfig,
        DEVELOP: DevelopmentConfig,
        PRODUCT: ProductionConfig,
    }
    config_class = config_map.get(mode, DevelopmentConfig)
    return config_class()
