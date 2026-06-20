"""配置模块路径常量。"""
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 文件上传配置
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_FILES_PER_REQUEST = 50
MAX_TEXT_LENGTH = 350000
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".json", ".js", ".ts", ".html", ".css",
    ".xml", ".yaml", ".yml", ".ini", ".conf", ".cfg", ".log", ".csv",
    ".sql", ".sh", ".bat", ".java", ".c", ".cpp", ".h", ".go", ".rs",
    ".rb", ".php", ".pdf", ".docx", ".xlsx",
}
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg",
}
