"""LLM 模型 API 路由。

接口总览：
- GET `/api/llm/providers`  获取已配置的 LLM 提供商列表及默认模型
"""
from flask import Blueprint, jsonify

from ..config import get_config
from ..services import get_llm_service
from ..utils import get_current_user

llm_bp = Blueprint("llm", __name__)


@llm_bp.route('/llm/providers', methods=['GET'])
def get_llm_providers():
    """获取系统中已配置的 LLM 模型提供商列表。

    用法:
    - 方法/路径: `GET /api/llm/providers`
    - 认证: Bearer Token
    - 成功响应: `{ "providers": [...], "default": "..." }`
    - 失败响应: 401 未登录；500 获取失败
    ---
    tags:
      - 模型
    summary: 获取可用的 LLM 模型提供商
    description: 返回系统中配置的所有可用的 LLM 模型提供商列表和默认提供商
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            providers:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: string
                    description: 提供商ID
                    example: "deepseek"
                  name:
                    type: string
                    description: 提供商名称
                    example: "DeepSeek"
                  models:
                    type: array
                    items:
                      type: string
                    description: 可用的模型列表
                    example: ["deepseek-chat", "deepseek-coder"]
            default:
              type: string
              description: 默认提供商ID
              example: "deepseek"
        examples:
          application/json:
            providers:
              - id: "deepseek"
                name: "DeepSeek"
                models: ["deepseek-chat", "deepseek-coder"]
            default: "deepseek"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        config = get_config()
        providers = get_llm_service().get_available_providers()

        return jsonify({
            'providers': providers,
            'default': config.LLM_DEFAULT_PROVIDER
        })
    except Exception as e:
        print(f"Get LLM providers error: {e}")
        return jsonify({'error': '获取模型列表失败'}), 500
