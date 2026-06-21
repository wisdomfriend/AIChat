"""应用配置与环境变量。

对外入口：
- `register_config(app)`  在应用工厂中挂载配置到 Flask 实例
- `get_config()`        在应用上下文中读取 `current_app` 上的配置
- `Config`              配置对象类型
- `DEVELOP` / `PRODUCT` 运行模式常量
- `resolve_log_dir()`   解析日志目录
"""
from flask import Flask, current_app

from backend.config.factory import (
    DEVELOP,
    PRODUCT,
    Config,
    create_config,
    resolve_log_dir,
)

APP_CONFIG_KEY = "app_config"

__all__ = [
    "Config",
    "DEVELOP",
    "PRODUCT",
    "get_config",
    "register_config",
    "resolve_log_dir",
]


def register_config(app: Flask, *, mode: str = DEVELOP) -> Config:
    """将配置对象挂载到 Flask 应用（环境变量需在入口脚本中预先 load_dotenv）。"""
    config_instance = create_config(mode=mode)
    app.extensions[APP_CONFIG_KEY] = config_instance
    return config_instance


def get_config() -> Config:
    """从当前 Flask 应用上下文读取配置。"""
    try:
        return current_app.extensions[APP_CONFIG_KEY]
    except RuntimeError as exc:
        raise RuntimeError("必须在 Flask 应用上下文中访问配置") from exc
    except KeyError as exc:
        raise RuntimeError("应用配置未初始化，请先调用 register_config(app)") from exc
