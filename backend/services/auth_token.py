"""Bearer Token 签发与鉴权。

职责总览（按认证流程）：
1) Token 工具
   - `_get_serializer()`   创建签名/验签器（内部使用）
   - `get_bearer_token()`  从请求头提取 Bearer token
2) Token 生命周期
   - `create_user_token()`  为已验证用户签发 token
   - `verify_user_token()`  校验签名、时效并返回 payload
3) 路由保护
   - `login_required`  API 登录鉴权装饰器
   - `sse_login_required`  SSE 流式 API 登录鉴权装饰器
   - `admin_required`  API 管理员鉴权装饰器
"""
import json
from functools import wraps

from flask import Response, current_app, request
from itsdangerous import BadSignature, BadTimeSignature, URLSafeTimedSerializer

from ..middleware.errors import UnauthorizedError


def _get_serializer() -> URLSafeTimedSerializer:
    """创建 token 签名/验签器（内部使用）。

    用法:
    - 调用方: `create_user_token()`、`verify_user_token()`
    - 密钥: `AUTH_TOKEN_SECRET`（缺省回退 `SECRET_KEY`）
    - salt: `user-auth`
    """
    secret = current_app.config.get("AUTH_TOKEN_SECRET") or current_app.config["SECRET_KEY"]
    return URLSafeTimedSerializer(secret_key=secret, salt="user-auth")


def create_user_token(user_id: int, username: str, is_admin: bool = False) -> str:
    """为已通过验证的用户签发 token。

    用法:
    - 调用方: `routes/auth.login`
    - 参数: `user_id`、`username`、`is_admin`
    - 返回值: URL-safe 签名字符串
    - Payload: `{ "uid", "u", "admin" }`
    - 有效期: `AUTH_TOKEN_MAX_AGE`（默认 86400 秒）
    """
    return _get_serializer().dumps(
        {
            "uid": user_id,
            "u": username,
            "admin": bool(is_admin),
        }
    )


def verify_user_token(token: str) -> dict | None:
    """验证 token 签名与时效，成功返回 payload。

    用法:
    - 调用方: `utils.get_current_user()`
    - 参数: `token` — Bearer token 字符串
    - 返回值: `{ user_id, username, is_admin }` 或 None
    - 捕获: BadSignature / BadTimeSignature → None（预期失败）
    """
    if not token:
        return None
    try:
        max_age = int(current_app.config.get("AUTH_TOKEN_MAX_AGE", 86400))
        payload = _get_serializer().loads(token, max_age=max_age)
    except (BadSignature, BadTimeSignature):
        return None
    user_id = payload.get("uid")
    username = payload.get("u")
    if not user_id or not username:
        return None
    return {
        "user_id": int(user_id),
        "username": str(username),
        "is_admin": bool(payload.get("admin", False)),
    }


def get_bearer_token() -> str:
    """从 Authorization 请求头提取 Bearer token。

    用法:
    - 调用方: `utils.get_current_user()`
    - 请求头: `Authorization: Bearer <token>`
    - 返回值: token 字符串；缺失或格式错误时返回空字符串
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return ""
    return auth.split(" ", 1)[1].strip()


def sse_error_response(message: str, status: int = 400) -> Response:
    """返回 SSE 格式的错误响应。"""
    payload = json.dumps({"type": "error", "message": message}, ensure_ascii=False)
    return Response(
        f"data: {payload}\n\n",
        mimetype="text/event-stream",
        status=status,
    )


def login_required(func):
    """API 登录鉴权装饰器。

    用法:
    - 装饰对象: 需登录的 API 路由
    - 请求头: `Authorization: Bearer <token>`
    - 失败: raise UnauthorizedError，由全局 handler 返回 JSON 401
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        from ..utils import get_current_user

        if not get_current_user():
            raise UnauthorizedError("未登录或登录已过期")
        return func(*args, **kwargs)

    return wrapper


def sse_login_required(func):
    """SSE 流式 API 登录鉴权装饰器。

    用法:
    - 装饰对象: 返回 text/event-stream 的需登录路由
    - 请求头: `Authorization: Bearer <token>`
    - 失败: 返回 SSE 格式 401（而非 JSON）
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        from ..utils import get_current_user

        if not get_current_user():
            return sse_error_response("未登录或登录已过期", status=401)
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    """API 管理员鉴权装饰器。

    用法:
    - 装饰对象: 需 admin 权限的 API 路由
    - 请求头: `Authorization: Bearer <token>`
    - 未登录: raise UnauthorizedError（401）
    - 非 admin: raise UnauthorizedError（401，无管理员权限）
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        from ..utils import get_current_user

        user = get_current_user()
        if not user:
            raise UnauthorizedError("未登录或登录已过期")
        if not user.get("is_admin", False):
            raise UnauthorizedError("无管理员权限")
        return func(*args, **kwargs)

    return wrapper
