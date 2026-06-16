"""健康检查路由。

接口总览：
1) 服务探活
   - GET `/health`  返回服务运行状态（公开，无需认证）
"""
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """服务健康检查（公开接口）。

    用法:
    - 方法/路径: `GET /health`
    - 认证: 无需登录
    - 成功响应: `{ "status": "ok", "service": "nginx-shop-api" }`
    - 说明: 该接口挂载在应用根路径，不在 `/api` 前缀下
    ---
    tags:
      - 系统
    summary: 服务健康检查
    description: 用于 Docker、Nginx 或负载均衡探活，返回 API 服务运行状态
    produces:
      - application/json
    responses:
      200:
        description: 服务正常
        schema:
          type: object
          properties:
            status:
              type: string
              description: 运行状态
              example: "ok"
            service:
              type: string
              description: 服务名称
              example: "nginx-shop-api"
        examples:
          application/json:
            status: "ok"
            service: "nginx-shop-api"
    """
    return jsonify({"status": "ok", "service": "nginx-shop-api"})
