"""WSGI入口文件 - 用于生产环境部署"""
import os
import logging
from dotenv import load_dotenv
from flask_app import create_app

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 尝试加载.env文件（如果存在）
env_path = load_dotenv()
if env_path:
    logger.info(f"已加载 .env 文件: {env_path}")
else:
    logger.warning("未找到 .env 文件，将使用环境变量或默认配置")
    logger.info("提示: 如果遇到数据库连接问题，请检查环境变量是否正确设置")
    logger.info("提示: 可以创建 .env 文件或通过系统环境变量设置数据库配置")

# 从环境变量获取配置名称，默认为production
config_name = os.environ.get('FLASK_ENV', 'production')
logger.info(f"使用配置: {config_name}")

# 创建应用实例（供gunicorn等WSGI服务器使用）
app = create_app(config_name)

