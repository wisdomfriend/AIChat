"""HTTP 请求相关工具。"""
from flask import request


def get_client_ip() -> str:
    """从代理头或 remote_addr 提取客户端 IP。"""
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    return request.remote_addr or "unknown"
