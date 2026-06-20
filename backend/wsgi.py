"""WSGI 入口文件 - 用于生产环境部署。"""
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

env_path = load_dotenv(BACKEND_DIR / ".env")
if env_path:
    logger.info("已加载 .env 文件: %s", env_path)
else:
    logger.warning("未找到 backend/.env 文件，将使用环境变量或默认配置")

config_name = os.environ.get("FLASK_ENV", "production")
logger.info("使用配置: %s", config_name)

from backend import create_app

app = create_app(config_name)
