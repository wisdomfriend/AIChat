"""应用配置与环境变量。

对外入口：
- `configure_app(app)`  在应用工厂中挂载配置到 Flask 实例
- `get_config()`        在应用上下文中读取 `current_app` 上的配置
- `Config`              配置对象类型
"""
from flask import Flask, current_app

from backend.config.factory import (
    DEVELOP,
    PRODUCT,
    Config,
    DevelopmentConfig,
    ProductionConfig,
    allowed_origins,
    create_config,
    resolve_log_dir,
)
from backend.config.settings import (
    ALLOWED_EXTENSIONS,
    DEEPSEEK_API_URL,
    DEFAULT_LOG_DIR,
    BACKEND_DIR,
    IMAGE_EXTENSIONS,
    MAX_FILE_SIZE,
    MAX_FILES_PER_REQUEST,
    MAX_TEXT_LENGTH,
    PROJECT_ROOT,
)

APP_CONFIG_KEY = "app_config"

__all__ = [
    "APP_CONFIG_KEY",
    "ALLOWED_EXTENSIONS",
    "Config",
    "DEEPSEEK_API_URL",
    "DEVELOP",
    "DevelopmentConfig",
    "BACKEND_DIR",
    "IMAGE_EXTENSIONS",
    "MAX_FILE_SIZE",
    "MAX_FILES_PER_REQUEST",
    "MAX_TEXT_LENGTH",
    "PRODUCT",
    "ProductionConfig",
    "PROJECT_ROOT",
    "DEFAULT_LOG_DIR",
    "allowed_origins",
    "configure_app",
    "create_config",
    "get_config",
    "resolve_log_dir",
]


def configure_app(app: Flask, *, config_name: str = "default") -> Config:
    """将配置对象挂载到 Flask 应用（环境变量需在入口脚本中预先 load_dotenv）。"""
    config_instance = create_config(config_name)
    app.extensions[APP_CONFIG_KEY] = config_instance
    app.config.from_object(config_instance)
    return config_instance


def get_config() -> Config:
    """从当前 Flask 应用上下文读取配置。"""
    try:
        return current_app.extensions[APP_CONFIG_KEY]
    except RuntimeError as exc:
        raise RuntimeError("必须在 Flask 应用上下文中访问配置") from exc
    except KeyError as exc:
        raise RuntimeError("应用配置未初始化，请先调用 configure_app(app)") from exc
