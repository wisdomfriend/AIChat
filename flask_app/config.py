"""应用配置文件"""
import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'guopengfei')
    
    # 数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'mysql')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'guopengfei')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'guopengfei')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'flask_app')
    
    def __init__(self):
        """初始化配置，验证必要的环境变量"""
        self._validate_config()
    
    def _validate_config(self):
        """验证配置是否完整"""
        # 在生产环境中，如果没有设置环境变量，给出警告
        if os.environ.get('FLASK_ENV') == 'production':
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
    
    # DeepSeek API配置
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    # Flask配置
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

