"""应用配置与环境变量。

职责总览：
1) 基础配置
   - `Config`  从环境变量读取 MySQL、Redis 限流、Bearer Token、LLM、搜索等配置
2) 环境变体
   - `DevelopmentConfig`  开发环境（DEBUG=True）
   - `ProductionConfig`   生产环境（DEBUG=False）
3) 工厂函数
   - `create_config()`  按名称创建配置实例（需在 load_dotenv 之后调用）
4) 辅助函数
   - `allowed_origins()`  CORS 允许的前端来源
   - `resolve_log_dir()`  应用日志目录
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

FLASK_APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FLASK_APP_DIR.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"


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
    # DeepSeek API配置（固定值，不需要从环境变量读取）
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    # 文件上传配置
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB (统一文件大小限制，包括文档和图片)
    MAX_FILES_PER_REQUEST = 50  # 一次最多50个文件（统一文件数量限制）
    MAX_TEXT_LENGTH = 350000  # 最大提取文本长度（字符数）
    ALLOWED_EXTENSIONS = {
        '.txt', '.md', '.py', '.json', '.js', '.ts', '.html', '.css',
        '.xml', '.yaml', '.yml', '.ini', '.conf', '.cfg', '.log', '.csv',
        '.sql', '.sh', '.bat', '.java', '.c', '.cpp', '.h', '.go', '.rs',
        '.rb', '.php', '.pdf', '.docx', '.xlsx'
    }
    # 图片格式
    IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'
    }
    
    def __init__(self):
        """加载环境变量并初始化 LLM、搜索配置。

        用法:
        - 调用方: `create_config()`、各 Service 直接实例化
        - 环境变量: `SECRET_KEY`、`MYSQL_*`、`REDIS_*`、`AUTH_TOKEN_*`、`LLM_*` 等
        - 副作用: 调用 `_validate_config()` 校验生产环境必填项
        """
        # 从环境变量读取配置（此时.env文件应该已经加载）
        self.SECRET_KEY = os.environ.get('SECRET_KEY', 'guopengfei')
        
        # 数据库配置
        self.MYSQL_HOST = os.environ.get('MYSQL_HOST', 'mysql')
        self.MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '23306'))
        self.MYSQL_USER = os.environ.get('MYSQL_USER', 'guopengfei')
        self.MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'guopengfei')
        self.MYSQL_DB = os.environ.get('MYSQL_DB', 'flask_app')
        
        # Redis 配置（聊天限流；应用工厂注入 REDIS_CLIENT）
        self.REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
        self.REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
        redis_password = os.environ.get('REDIS_PASSWORD', None)
        if redis_password in (None, '', 'None', 'null', 'NULL'):
            self.REDIS_PASSWORD = None
        else:
            self.REDIS_PASSWORD = redis_password
        self.REDIS_CLIENT = None  # 应用初始化时注入

        # Bearer Token 认证（React 前后端分离）
        self.AUTH_TOKEN_SECRET = os.environ.get('AUTH_TOKEN_SECRET', self.SECRET_KEY)
        self.AUTH_TOKEN_MAX_AGE = int(os.environ.get('AUTH_TOKEN_MAX_AGE', '86400'))

        # Flask配置
        self.FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
        
        # PostgreSQL（LangGraph checkpointer）
        self.POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'postgres')
        self.POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', '5432'))
        self.POSTGRES_USER = os.environ.get('POSTGRES_USER', 'langgraph')
        self.POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'langgraph')
        self.POSTGRES_DB = os.environ.get('POSTGRES_DB', 'langgraph')

        # Agent 配置（SummarizationMiddleware）
        self.AGENT_SUMMARY_TRIGGER_FRACTION = float(os.environ.get('AGENT_SUMMARY_TRIGGER_FRACTION', '0.8'))
        self.AGENT_SUMMARY_KEEP_MESSAGES = int(os.environ.get('AGENT_SUMMARY_KEEP_MESSAGES', '20'))
        self.AGENT_RECURSION_LIMIT = int(os.environ.get('AGENT_RECURSION_LIMIT', '25'))
        
        # LLM 模型配置
        self._init_llm_providers()
        
        # 联网搜索配置（Tavily + 百度）
        self._init_web_search_config()
        
        # 验证配置
        self._validate_config()
    
    def _init_llm_providers(self):
        """初始化 LLM 模型提供商配置（当前仅 DeepSeek）"""
        self.DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
        self.LLM_PROVIDERS = {
            'deepseek': {
                'type': 'openai_compatible',
                'base_url': 'https://api.deepseek.com/v1',
                'api_key': self.DEEPSEEK_API_KEY,
                'model_name': 'deepseek-v4-flash',
                'display_name': 'deepseek-v4-flash',
                'max_context_length': 512000,
                'supports_images': False,
                'enabled': True
            },
        }
        
        self.LLM_DEFAULT_PROVIDER = 'deepseek'
    
    def _init_web_search_config(self):
        """初始化联网搜索配置"""
        self.TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')
        self.TAVILY_SEARCH_MAX_RESULTS = int(os.environ.get('TAVILY_SEARCH_MAX_RESULTS', '3'))
        self.BAIDU_SEARCH_MAX_RESULTS = int(os.environ.get('BAIDU_SEARCH_MAX_RESULTS', '3'))
    
    def _validate_config(self):
        """验证配置是否完整"""
        # 在生产环境中，如果没有设置环境变量，给出警告
        if self.FLASK_ENV == 'production':
            if not os.environ.get('MYSQL_HOST'):
                logger.warning("警告: 生产环境中未设置 MYSQL_HOST 环境变量，使用默认值 'mysql'")
            if not os.environ.get('MYSQL_USER'):
                logger.warning("警告: 生产环境中未设置 MYSQL_USER 环境变量，使用默认值")
            if not os.environ.get('MYSQL_PASSWORD'):
                logger.warning("警告: 生产环境中未设置 MYSQL_PASSWORD 环境变量，使用默认值")
            if not os.environ.get('MYSQL_DB'):
                logger.warning("警告: 生产环境中未设置 MYSQL_DB 环境变量，使用默认值")
    
    @property
    def DATABASE_URL(self):
        """构建 SQLAlchemy MySQL 连接 URL。

        用法:
        - 调用方: `database.get_database_url()`
        - 返回值: `mysql+pymysql://user:pass@host:port/db`
        """
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

    @property
    def POSTGRES_URI(self):
        """构建 LangGraph Postgres checkpointer 连接 URI。"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class DevelopmentConfig(Config):
    """开发环境配置（DEBUG=True）。"""
    def __init__(self):
        super().__init__()
        self.DEBUG = True


class ProductionConfig(Config):
    """生产环境配置（DEBUG=False）。"""
    def __init__(self):
        super().__init__()
        self.DEBUG = False


def create_config(config_name='default'):
    """按名称创建配置实例。

    用法:
    - 调用方: `flask_app.create_app()`
    - 参数: `config_name` — `development` / `production` / `default`
    - 返回值: 已加载环境变量的 Config 子类实例
    - 注意: 需在 `load_dotenv()` 之后调用，否则读不到 `.env`
    """
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'default': DevelopmentConfig
    }
    
    config_class = config_map.get(config_name, DevelopmentConfig)
    return config_class()

