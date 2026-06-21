"""Bearer Token 认证 API 路由。

接口总览（按用户使用流程）：
1) 登录/注册
   - POST `/api/auth/login`     校验用户名密码并返回 token
   - POST `/api/auth/register`  注册新用户
2) 会话信息
   - GET  `/api/auth/me`        获取当前登录用户（需 Bearer token）
   - POST `/api/auth/logout`    登出（需 Bearer token；前端清除 token 即可）
3) 调试
   - GET  `/api/test-auth`      调试 Bearer 认证状态（开发用）
"""
from flask import Blueprint, jsonify, request

from ..middleware.errors import BadRequestError
from ..services import AuthService
from ..services.auth_token import create_user_token, get_bearer_token, login_required
from ..utils import get_current_user, serialize_user

auth_bp = Blueprint("auth", __name__)
auth_debug_bp = Blueprint("auth_debug", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """用户登录，返回 Bearer token。

    用法:
    - 方法/路径: `POST /api/auth/login`
    - 认证: 无需登录
    - 请求体: `{ "username": "...", "password": "..." }`
    - 成功响应: `{ "token": "...", "user": { id, username, is_admin, ... } }`
    - 失败响应: 400 参数错误或凭证无效
    ---
    tags:
      - 认证
    summary: 用户登录
    description: 校验用户名与密码，成功后返回 Bearer Token 及用户信息
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: 用户名
              example: "demo_user"
            password:
              type: string
              description: 密码
              example: "password123"
    responses:
      200:
        description: 登录成功
        schema:
          type: object
          properties:
            token:
              type: string
              description: Bearer Token
              example: "eyJ1c2VyIjoiZGVtbyJ9..."
            user:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                username:
                  type: string
                  example: "demo_user"
                is_admin:
                  type: boolean
                  example: false
                last_login:
                  type: string
                  format: date-time
                  example: "2024-01-01T12:00:00"
        examples:
          application/json:
            token: "eyJ1c2VyIjoiZGVtbyJ9..."
            user:
              id: 1
              username: "demo_user"
              is_admin: false
              last_login: "2024-01-01T12:00:00"
      400:
        description: 参数错误或凭证无效
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 400
            message:
              type: string
              example: "用户名或密码错误！"
            error:
              type: string
              example: "用户名或密码错误！"
    """
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        raise BadRequestError("用户名和密码不能为空")

    result = AuthService.authenticate(username, password)
    if not result.get("success"):
        raise BadRequestError(result.get("message", "登录失败"))

    user = result["user"]
    token = create_user_token(user["id"], user["username"], user.get("is_admin", False))
    return jsonify({"token": token, "user": serialize_user(user)})


@auth_bp.route("/register", methods=["POST"])
def register():
    """用户注册。

    用法:
    - 方法/路径: `POST /api/auth/register`
    - 认证: 无需登录
    - 请求体: `{ "username": "...", "password": "...", "password_confirm": "..." }`
    - 成功响应: `{ "message": "注册成功！", "user": { id, username } }`
    - 失败响应: 400 用户名重复、格式不符或密码不一致
    ---
    tags:
      - 认证
    summary: 用户注册
    description: 创建新用户账号，用户名 3-20 位字母数字下划线，密码至少 6 位
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: 用户名（3-20 位，字母数字下划线）
              example: "new_user"
            password:
              type: string
              description: 密码（至少 6 位）
              example: "password123"
            password_confirm:
              type: string
              description: 确认密码（可选，若提供则须与 password 一致）
              example: "password123"
    responses:
      200:
        description: 注册成功
        schema:
          type: object
          properties:
            message:
              type: string
              example: "注册成功！"
            user:
              type: object
              properties:
                id:
                  type: integer
                  example: 2
                username:
                  type: string
                  example: "new_user"
        examples:
          application/json:
            message: "注册成功！"
            user:
              id: 2
              username: "new_user"
      400:
        description: 注册失败
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 400
            message:
              type: string
              example: "该用户名已被注册，请选择其他用户名！"
            error:
              type: string
              example: "该用户名已被注册，请选择其他用户名！"
    """
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    password_confirm = data.get("password_confirm")

    result = AuthService.register(username, password, password_confirm)
    if not result.get("success"):
        raise BadRequestError(result.get("message", "注册失败"))

    return jsonify(
        {
            "message": result.get("message", "注册成功"),
            "user": result.get("user"),
        }
    )


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    """获取当前登录用户信息。

    用法:
    - 方法/路径: `GET /api/auth/me`
    - 请求头: `Authorization: Bearer <token>`
    - 成功响应: `{ "user": { id, username, is_admin, last_login } }`
    - 失败响应: 401 未登录或 token 无效/过期
    ---
    tags:
      - 认证
    summary: 获取当前用户信息
    description: 根据 Bearer Token 返回当前登录用户的资料
    produces:
      - application/json
    security:
      - bearerAuth: []
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            user:
              type: object
              properties:
                id:
                  type: integer
                  example: 1
                username:
                  type: string
                  example: "demo_user"
                is_admin:
                  type: boolean
                  example: false
                last_login:
                  type: string
                  format: date-time
                  example: "2024-01-01T12:00:00"
        examples:
          application/json:
            user:
              id: 1
              username: "demo_user"
              is_admin: false
              last_login: "2024-01-01T12:00:00"
      401:
        description: 未登录或 token 无效/过期
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 401
            message:
              type: string
              example: "未登录或登录已过期"
            error:
              type: string
              example: "未登录或登录已过期"
    """
    user = get_current_user()
    return jsonify({"user": serialize_user(user)})


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """用户登出。

    用法:
    - 方法/路径: `POST /api/auth/logout`
    - 请求头: `Authorization: Bearer <token>`
    - 成功响应: `{ "message": "已登出" }`
    - 说明: token 为无状态签名，服务端不维护黑名单；前端清除 localStorage 即完成登出
    ---
    tags:
      - 认证
    summary: 用户登出
    description: 语义化登出接口；Token 无状态，前端清除 localStorage 中的 token 即可完成登出
    produces:
      - application/json
    security:
      - bearerAuth: []
    responses:
      200:
        description: 登出成功
        schema:
          type: object
          properties:
            message:
              type: string
              example: "已登出"
        examples:
          application/json:
            message: "已登出"
      401:
        description: 未登录或 token 无效/过期
        schema:
          type: object
          properties:
            code:
              type: integer
              example: 401
            message:
              type: string
              example: "未登录或登录已过期"
            error:
              type: string
              example: "未登录或登录已过期"
    """
    return jsonify({"message": "已登出"})


@auth_debug_bp.route("/test-auth", methods=["GET"])
def test_auth():
    """调试当前 Bearer 认证状态（开发用）。

    用法:
    - 方法/路径: `GET /api/test-auth`
    - 认证: 可选 Bearer Token
    - 成功响应: `{ "authenticated": bool, "user": {...}, "has_bearer_token": bool }`
    ---
    tags:
      - 认证
    summary: 测试当前用户的 Bearer 认证状态
    description: 用于调试，检查 Authorization 请求头中的 Bearer Token 是否有效
    produces:
      - application/json
    responses:
      200:
        description: 认证状态
    """
    user = get_current_user()
    token = get_bearer_token()
    return jsonify({
        "authenticated": user is not None,
        "user": serialize_user(user),
        "has_bearer_token": bool(token),
        "token_preview": f"{token[:16]}..." if token and len(token) > 16 else (token or None),
    })
