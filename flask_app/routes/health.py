"""健康检查路由。"""
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
def health_check():
    """服务健康检查（公开接口）。"""
    return jsonify({"status": "ok", "service": "nginx-shop-api"})
