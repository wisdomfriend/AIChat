"""应用配置文件"""
import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """基础配置"""
    # DeepSeek API配置（固定值，不需要从环境变量读取）
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    def __init__(self):
        """初始化配置，从环境变量读取配置值"""
        # 从环境变量读取配置（此时.env文件应该已经加载）
        self.SECRET_KEY = os.environ.get('SECRET_KEY', 'guopengfei')
        
        # 数据库配置
        self.MYSQL_HOST = os.environ.get('MYSQL_HOST', 'mysql')
        self.MYSQL_USER = os.environ.get('MYSQL_USER', 'guopengfei')
        self.MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'guopengfei')
        self.MYSQL_DB = os.environ.get('MYSQL_DB', 'flask_app')
        
        # Redis配置
        self.REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
        self.REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
        # 处理REDIS_PASSWORD：如果为空字符串、"None"或"null"，则设为None
        redis_password = os.environ.get('REDIS_PASSWORD', None)
        if redis_password in (None, '', 'None', 'null', 'NULL'):
            self.REDIS_PASSWORD = None
        else:
            self.REDIS_PASSWORD = redis_password
        
        # Session配置 - 使用Redis存储Session
        self.SESSION_TYPE = 'redis'
        self.SESSION_REDIS = None  # 将在应用初始化时设置
        # Session过期时间：7天（单位：秒）
        self.PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME', '604800'))  # 默认7天
        self.SESSION_PERMANENT = True  # 启用永久Session
        self.SESSION_USE_SIGNER = True  # 对Session ID进行签名，增强安全性
        self.SESSION_KEY_PREFIX = 'session:'  # Redis中Session的键前缀
        
        # Flask配置
        self.FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
        
        # 验证配置
        self._validate_config()
    
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
        """构建数据库连接URL"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}/{self.MYSQL_DB}"


class DevelopmentConfig(Config):
    """开发环境配置"""
    def __init__(self):
        super().__init__()
        self.DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    def __init__(self):
        super().__init__()
        self.DEBUG = False


def create_config(config_name='default'):
    """
    配置工厂函数
    
    在创建配置实例时读取环境变量，确保.env文件已经加载
    
    Args:
        config_name: 配置名称 ('development', 'production', 'default')
    
    Returns:
        配置类实例
    """
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'default': DevelopmentConfig
    }
    
    config_class = config_map.get(config_name, DevelopmentConfig)
    return config_class()

