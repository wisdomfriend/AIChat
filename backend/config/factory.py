"""按运行环境创建应用配置对象。"""
import logging
import os
from pathlib import Path

from backend.config.settings import DEFAULT_LOG_DIR, MAX_FILE_SIZE

logger = logging.getLogger(__name__)

DEVELOP = "development"
PRODUCT = "production"


def resolve_log_dir() -> Path:
    """解析应用日志存储目录。"""
    env_dir = os.environ.get("LOG_DIR", "").strip()
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return DEFAULT_LOG_DIR


class Config:
    """基础配置，实例化时从环境变量加载全部运行时参数。"""

    MAX_FILE_SIZE = MAX_FILE_SIZE

    def __init__(self):
        self.AUTH_TOKEN_SECRET = os.environ.get("AUTH_TOKEN_SECRET")
        self.AUTH_TOKEN_MAX_AGE = int(os.environ.get("AUTH_TOKEN_MAX_AGE", "86400"))

        self.MYSQL_HOST = os.environ.get("MYSQL_HOST", "mysql")
        self.MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "23306"))
        self.MYSQL_USER = os.environ.get("MYSQL_USER", "guopengfei")
        self.MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "guopengfei")
        self.MYSQL_DB = os.environ.get("MYSQL_DB", "backend")

        self.REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
        self.REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
        self.REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
        self.REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", None)
        self.REDIS_CLIENT = None

        self.POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
        self.POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER = os.environ.get("POSTGRES_USER", "langgraph")
        self.POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "langgraph")
        self.POSTGRES_DB = os.environ.get("POSTGRES_DB", "langgraph")

        self.AGENT_SUMMARY_TRIGGER_FRACTION = float(os.environ.get("AGENT_SUMMARY_TRIGGER_FRACTION", "0.8"))
        self.AGENT_SUMMARY_KEEP_MESSAGES = int(os.environ.get("AGENT_SUMMARY_KEEP_MESSAGES", "20"))
        self.AGENT_RECURSION_LIMIT = int(os.environ.get("AGENT_RECURSION_LIMIT", "25"))

        self.TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
        self.TAVILY_SEARCH_MAX_RESULTS = int(os.environ.get("TAVILY_SEARCH_MAX_RESULTS", "3"))
        self.BAIDU_SEARCH_MAX_RESULTS = int(os.environ.get("BAIDU_SEARCH_MAX_RESULTS", "3"))

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

        self.KB_EMBEDDING_API_URL = os.environ.get("KB_EMBEDDING_API_URL", "")
        self.KB_EMBEDDING_API_KEY = os.environ.get("KB_EMBEDDING_API_KEY", "")
        self.KB_EMBEDDING_MODEL = os.environ.get("KB_EMBEDDING_MODEL", "embedding")
        self.KB_EMBEDDING_DIMENSION = int(os.environ.get("KB_EMBEDDING_DIMENSION", "512"))
        self.KB_EMBEDDING_TIMEOUT = int(os.environ.get("KB_EMBEDDING_TIMEOUT", "60"))

        self.KB_RERANK_API_URL = os.environ.get("KB_RERANK_API_URL", "")
        self.KB_RERANK_API_KEY = os.environ.get("KB_RERANK_API_KEY", "")
        self.KB_RERANK_MODEL = os.environ.get("KB_RERANK_MODEL", "rerank")
        self.KB_RERANK_TIMEOUT = int(os.environ.get("KB_RERANK_TIMEOUT", "60"))

        self.KB_CHUNK_SIZE = int(os.environ.get("KB_CHUNK_SIZE", "800"))
        self.KB_CHUNK_OVERLAP = int(os.environ.get("KB_CHUNK_OVERLAP", "100"))
        self.KB_TOP_K = int(os.environ.get("KB_TOP_K", "5"))
        self.KB_VECTOR_CANDIDATES = int(os.environ.get("KB_VECTOR_CANDIDATES", "20"))
        self.KB_BM25_CANDIDATES = int(os.environ.get("KB_BM25_CANDIDATES", "20"))
        self.KB_RRF_K = int(os.environ.get("KB_RRF_K", "60"))
        self.KB_RERANK_CANDIDATES = int(os.environ.get("KB_RERANK_CANDIDATES", "20"))

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
    if mode not in (DEVELOP, PRODUCT):
        raise RuntimeError(
            f"不支持的运行模式: {mode!r}，仅允许 {DEVELOP!r} 或 {PRODUCT!r}"
        )
    config_map = {
        DEVELOP: DevelopmentConfig,
        PRODUCT: ProductionConfig,
    }
    config_class = config_map.get(mode, DevelopmentConfig)
    return config_class()
