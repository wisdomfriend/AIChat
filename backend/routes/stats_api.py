"""Token 统计 JSON API（阶段 4）。

接口总览：
- GET `/api/stats/user`   当前用户 Token 用量（需登录）
- GET `/api/stats/admin`  全局统计与最近用量（需 admin）
"""
from flask import Blueprint, jsonify

from ..middleware.errors import AppError
from ..services import StatsService
from ..services.auth_token import admin_required, login_required
from ..utils import get_current_user

stats_api_bp = Blueprint("stats_api", __name__)


def _serialize_token_usage(usage) -> dict:
    request_time = usage.request_time
    return {
        "id": usage.id,
        "user_id": usage.user_id,
        "prompt_tokens": usage.prompt_tokens or 0,
        "completion_tokens": usage.completion_tokens or 0,
        "total_tokens": usage.total_tokens or 0,
        "model": usage.model or "",
        "request_time": request_time.isoformat() if request_time else None,
    }


@stats_api_bp.route("/user", methods=["GET"])
@login_required
def get_user_stats():
    """获取当前登录用户的 Token 用量汇总。

    用法:
    - 方法/路径: `GET /api/stats/user`
    - 认证: Bearer Token
    - 成功响应: `{ "stats": { today, week, month, total } }`
    ---
    tags:
      - 统计
    summary: 获取当前用户 Token 统计
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
      401:
        description: 未登录
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    stats_service = StatsService()
    stats = stats_service.get_user_stats(user["id"])
    return jsonify({"stats": stats})


@stats_api_bp.route("/admin", methods=["GET"])
@admin_required
def get_admin_stats():
    """获取全局 Token 统计与最近使用记录（admin）。

    用法:
    - 方法/路径: `GET /api/stats/admin`
    - 认证: Bearer Token，需 admin
    - 成功响应: `{ "stats": {...}, "recent_usage": [...] }`
    ---
    tags:
      - 统计
    summary: 获取全局 Token 统计（管理员）
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
      401:
        description: 未登录或无管理员权限
    security:
      - bearerAuth: []
    """
    try:
        stats_service = StatsService()
        admin_data = stats_service.get_admin_stats()
        recent_usage = [_serialize_token_usage(item) for item in admin_data.get("recent_usage", [])]
        return jsonify(
            {
                "stats": admin_data.get("stats", {}),
                "recent_usage": recent_usage,
            }
        )
    except Exception as e:
        print(f"Get admin stats API error: {e}")
        raise AppError("获取管理统计失败", status_code=500)
