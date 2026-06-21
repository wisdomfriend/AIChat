"""配置模块路径常量。"""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# 默认logs 目录
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

# 文件上传配置
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
