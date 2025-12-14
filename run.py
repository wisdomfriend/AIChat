"""Flask应用启动脚本 - 用于开发环境和PyCharm调试"""
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

# 从环境变量获取配置名称，默认为development（开发环境）
config_name = os.environ.get('FLASK_ENV', 'development')
logger.info(f"使用配置: {config_name}")

# 创建应用实例
app = create_app(config_name)

if __name__ == '__main__':
    # 开发环境默认启用debug模式
    debug_mode = app.config.get('DEBUG', True)
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)

