"""业务异常与统一错误响应。

设计原则：
1) Router 可通过 `raise AppError` 表达可预期的 4xx
2) 全局 error handler 统一序列化为 JSON（API）或简单 HTML（页面）
3) 未捕获异常 → 500，exception 日志（不泄露内部细节）
"""
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException


class AppError(Exception):
    """可预期的业务异常，由全局 handler 转为响应。"""

    status_code: int = 400

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class BadRequestError(AppError):
    """400 — 参数或业务规则不满足。"""

    status_code = 400


class UnauthorizedError(AppError):
    """401 — 未登录或凭证无效。"""

    status_code = 401


class NotFoundError(AppError):
    """404 — 目标资源不存在。"""

    status_code = 404


def _wants_json_response() -> bool:
    """API 路径或客户端优先接受 JSON 时返回 JSON 错误体。"""
    if request.path.startswith("/api/"):
        return True
    best = request.accept_mimetypes.best_match(["application/json", "text/html"])
    if best == "application/json":
        return request.accept_mimetypes[best] > request.accept_mimetypes["text/html"]
    return False


def _error_response(code: int, message: str):
    """统一错误 JSON；保留 `error` 字段以兼容现有 API 路由。"""
    return jsonify({"code": code, "message": message, "error": message}), code


def _html_error_response(code: int, message: str):
    return (
        f"<h1>{code}</h1><p>{message}</p>",
        code,
        {"Content-Type": "text/html; charset=utf-8"},
    )


def register_error_handlers(app: Flask) -> None:
    """注册全局错误处理器。"""

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        app.logger.warning("AppError [%s]: %s", error.status_code, error.message)
        if _wants_json_response():
            return _error_response(error.status_code, error.message)
        return _html_error_response(error.status_code, error.message)

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        code = error.code or 500
        message = error.description or error.name or "请求错误"
        if code >= 500:
            app.logger.exception("HTTPException [%s]: %s", code, message)
        else:
            app.logger.warning("HTTPException [%s]: %s", code, message)
        if _wants_json_response():
            return _error_response(code, message)
        return _html_error_response(code, message)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled exception: %s", error)
        if _wants_json_response():
            return _error_response(500, "服务器内部错误")
        return _html_error_response(500, "服务器内部错误")
