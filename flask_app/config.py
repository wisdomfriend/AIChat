"""应用配置文件"""
import os


class Config:
    """基础配置"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'guopengfei_learning_secret_key_2024')
    
    # 数据库配置
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'mysql')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'guopengfei_learning')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Gpf_learning')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'nginx_shop')
    
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

