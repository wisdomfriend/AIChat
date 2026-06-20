"""请求日志中间件。"""
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, request

from ..config import resolve_log_dir
from ..utils import get_client_ip


def _ensure_file_handler(app: Flask) -> None:
    """确保 app.logger 已挂载文件 handler，避免重复注册。"""
    log_dir = resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"
    log_path = str(log_file)

    for handler in app.logger.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename == log_path:
            return

    handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def register_request_logging(app: Flask) -> None:
    """注册 before_request 钩子，记录每个请求并写入日志文件。"""
    _ensure_file_handler(app)

    @app.before_request
    def log_request():
        if request.path.startswith("/static/"):
            return
        app.logger.info("%s %s [%s]", request.method, request.path, get_client_ip())
