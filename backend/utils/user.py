"""用户认证与序列化工具。"""
from backend.db import User, get_session
from backend.services.auth_token import get_bearer_token, verify_user_token


def serialize_user(user: dict | None) -> dict | None:
    """将用户 dict 序列化为 API 响应格式。"""
    if not user:
        return None
    last_login = user.get("last_login")
    if last_login is not None and hasattr(last_login, "isoformat"):
        last_login = last_login.isoformat()
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "last_login": last_login,
        "is_admin": bool(user.get("is_admin", False)),
    }


def _user_row_to_dict(user: User) -> dict:
    """将 ORM User 转为 API 内部使用的用户 dict。"""
    return {
        "id": user.id,
        "username": user.username,
        "last_login": user.last_login,
        "is_admin": bool(user.is_admin) if hasattr(user, "is_admin") else False,
    }


def get_current_user():
    """从 Bearer Token 读取当前登录用户。"""
    token = get_bearer_token()
    if not token:
        return None

    payload = verify_user_token(token)
    if not payload:
        return None

    try:
        db = get_session()
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        db.close()

        if user and user.is_active:
            return _user_row_to_dict(user)
    except Exception as e:
        print(f"Get user error: {e}")

    return None
