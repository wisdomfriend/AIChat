"""跨域中间件。"""
from flask import Flask, make_response, request

from ..config import allowed_origins


def _apply_cors_headers(response, origin: str, origins: list[str]):
    if "*" in origins:
        response.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    elif origins:
        response.headers["Access-Control-Allow-Origin"] = origins[0]
        response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Cookie"
    response.headers["Vary"] = "Origin"
    return response


def register_cors(app: Flask) -> None:
    """注册 CORS 响应头与 OPTIONS 预检处理。"""

    @app.before_request
    def handle_preflight():
        if request.method != "OPTIONS":
            return None
        response = make_response()
        return _apply_cors_headers(response, request.headers.get("Origin", ""), allowed_origins())

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin", "")
        return _apply_cors_headers(response, origin, allowed_origins())
