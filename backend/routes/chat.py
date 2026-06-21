"""聊天与会话 API 路由。

接口总览（按用户使用流程）：
1) 发送消息
   - POST `/api/chat`  发送消息并返回 SSE 流式响应（支持附件、知识库、模型选择）
2) 会话管理
   - GET    `/api/sessions`                      获取当前用户的会话列表
   - GET    `/api/sessions/<session_id>/messages`  获取会话消息历史
   - PATCH  `/api/sessions/<session_id>`       更新会话（如固定/取消固定）
   - DELETE `/api/sessions/<session_id>`       删除会话
"""
import json

from flask import Blueprint, Response, jsonify, request, stream_with_context

from ..config import get_config
from ..services import ChatService, get_agent_service, get_llm_service
from ..services.auth_token import sse_login_required
from ..utils import get_current_user, rate_limit_chat

chat_bp = Blueprint("chat", __name__)


@chat_bp.route('/chat', methods=['POST'])
@sse_login_required
@rate_limit_chat
def api_chat():
    """发送聊天消息，返回 SSE 流式响应。

    用法:
    - 方法/路径: `POST /api/chat`
    - 认证: Bearer Token
    - 请求体: `{ "message": "...", "session_id": 1, "file_ids": [], "llm_provider": "...", "knowledge_base_ids": [] }`
    - 成功响应: `text/event-stream`，事件 `{ "type": "chunk"|"end"|"error", ... }`
    - 失败响应: 401 未登录；400 参数错误；429 访问过于频繁
    ---
    tags:
      - 聊天
    summary: 发送消息并获取流式响应
    description: |
      发送聊天消息，支持会话管理和文件附件。
      返回 Server-Sent Events (SSE) 流式响应。
      需要用户登录（通过 Session Cookie 认证）。
    consumes:
      - application/json
    produces:
      - text/event-stream
    parameters:
      - in: body
        name: body
        description: 聊天请求参数
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              description: 用户消息内容（最大 64KB）
              example: "你好，请介绍一下自己"
            session_id:
              type: integer
              description: 会话ID，如果为空则创建新会话
              example: 1
            file_ids:
              type: array
              items:
                type: integer
              description: 附加的文件ID列表
              example: [1, 2]
            llm_provider:
              type: string
              description: 模型提供商ID（可选）
              example: "deepseek"
            knowledge_base_ids:
              type: array
              items:
                type: integer
              description: 选中的知识库 ID 列表（可选，Agent 将优先检索内部文档）
              example: [1]
    responses:
      200:
        description: 流式响应成功
        schema:
          type: string
        examples:
          text/event-stream:
            data: {"type":"chunk","content":"你好"}
            data: {"type":"chunk","content":"，"}
            data: {"type":"end","session_id":1}
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            type:
              type: string
              example: "error"
            message:
              type: string
              example: "消息不能为空"
      401:
        description: 未登录
        schema:
          type: object
          properties:
            type:
              type: string
              example: "error"
            message:
              type: string
              example: "未登录"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()

    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id')  # 会话ID，如果为None则创建新会话
        file_ids = data.get('file_ids', [])  # 附加的文件ID列表
        llm_provider = data.get('llm_provider')  # 模型提供商ID（可选）
        knowledge_base_ids = data.get('knowledge_base_ids', [])
        
        if not message:
            return Response(
                'data: {"type":"error","message":"消息不能为空"}\n\n',
                mimetype='text/event-stream',
                status=400
            )
        
        # 检查消息长度限制（64KB = 65536 字节）
        MAX_MESSAGE_SIZE = 64 * 1024  # 64KB
        message_size = len(message.encode('utf-8'))
        if message_size > MAX_MESSAGE_SIZE:
            return Response(
                f'data: {{"type":"error","message":"消息过长，当前大小：{message_size} 字节，最大允许：{MAX_MESSAGE_SIZE} 字节（64KB）"}}\n\n',
                mimetype='text/event-stream',
                status=400
            )
        
        chat_service = ChatService(
            agent_service=get_agent_service(),
            llm_service=get_llm_service(),
            config=get_config(),
        )
        
        def generate():
            """生成SSE流"""
            try:
                for chunk in chat_service.process_chat_stream_with_session(
                    user['id'], 
                    session_id, 
                    message,
                    file_ids,
                    llm_provider,
                    knowledge_base_ids,
                ):
                    yield chunk
            except Exception as e:
                print(f"Stream generation error: {e}")
                yield f'data: {json.dumps({"type": "error", "message": f"流式响应错误: {str(e)}"})}\n\n'
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive'
            }
        )
            
    except Exception as e:
        print(f"Chat API error: {e}")
        return Response(
            f'data: {json.dumps({"type": "error", "message": f"处理请求时出错: {str(e)}"})}\n\n',
            mimetype='text/event-stream',
            status=500
        )


@chat_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """获取当前用户的全部聊天会话。

    用法:
    - 方法/路径: `GET /api/sessions`
    - 认证: Bearer Token
    - 成功响应: `{ "sessions": [...] }`
    - 失败响应: 401 未登录；500 获取失败
    ---
    tags:
      - 会话
    summary: 获取当前用户的所有会话
    description: 返回当前登录用户的所有聊天会话列表，按创建时间倒序排列
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            sessions:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: 会话ID
                    example: 1
                  title:
                    type: string
                    description: 会话标题
                    example: "关于Python的问题"
                  created_at:
                    type: string
                    format: date-time
                    description: 创建时间
                    example: "2024-01-01T12:00:00"
                  updated_at:
                    type: string
                    format: date-time
                    description: 更新时间
                    example: "2024-01-01T12:30:00"
                  message_count:
                    type: integer
                    description: 消息数量
                    example: 10
        examples:
          application/json:
            sessions:
              - id: 1
                title: "关于Python的问题"
                created_at: "2024-01-01T12:00:00"
                updated_at: "2024-01-01T12:30:00"
                message_count: 10
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
        chat_service = ChatService(
            agent_service=get_agent_service(),
            llm_service=get_llm_service(),
            config=get_config(),
        )
        sessions = chat_service.get_sessions(user['id'])
        return jsonify({'sessions': sessions})
    except Exception as e:
        print(f"Get sessions error: {e}")
        return jsonify({'error': '获取会话列表失败'}), 500


@chat_bp.route('/sessions/<int:session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """获取指定会话的全部消息（含附件信息）。

    用法:
    - 方法/路径: `GET /api/sessions/<session_id>/messages`
    - 认证: Bearer Token
    - 成功响应: `{ "messages": [...] }`
    - 失败响应: 401 未登录；404 会话不存在或无权限；500 获取失败
    ---
    tags:
      - 会话
    summary: 获取指定会话的所有消息
    description: 返回指定会话的所有消息列表，包括用户消息和AI回复，以及关联的文件信息
    produces:
      - application/json
    parameters:
      - in: path
        name: session_id
        type: integer
        required: true
        description: 会话ID
        example: 1
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            messages:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: 消息ID
                    example: 1
                  role:
                    type: string
                    description: 消息角色（user 或 assistant）
                    example: "user"
                  content:
                    type: string
                    description: 消息内容
                    example: "你好"
                  created_at:
                    type: string
                    format: date-time
                    description: 创建时间
                    example: "2024-01-01T12:00:00"
                  files:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: integer
                        filename:
                          type: string
                        file_type:
                          type: string
        examples:
          application/json:
            messages:
              - id: 1
                role: "user"
                content: "你好"
                created_at: "2024-01-01T12:00:00"
                files: []
              - id: 2
                role: "assistant"
                content: "你好！有什么可以帮助你的吗？"
                created_at: "2024-01-01T12:00:05"
                files: []
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      404:
        description: 会话不存在或无权限
        schema:
          type: object
          properties:
            error:
              type: string
              example: "会话不存在或无权限"
      500:
        description: 服务器内部错误
    security:
      - bearerAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        chat_service = ChatService(
            agent_service=get_agent_service(),
            llm_service=get_llm_service(),
            config=get_config(),
        )
        # 包含文件信息
        messages = chat_service.get_session_messages(session_id, user['id'], include_files=True)
        
        if messages is None:
            return jsonify({'error': '会话不存在或无权限'}), 404
        
        return jsonify({'messages': messages})
    except Exception as e:
        print(f"Get session messages error: {e}")
        return jsonify({'error': '获取消息失败'}), 500


@chat_bp.route('/sessions/<int:session_id>', methods=['PATCH'])
def update_session(session_id):
    """更新会话属性（如固定状态）。

    用法:
    - 方法/路径: `PATCH /api/sessions/<session_id>`
    - 认证: Bearer Token
    - 请求体: `{ "pinned": true }`
    - 成功响应: `{ "success": true, "is_pinned": true }`
    - 失败响应: 400 缺少参数；401 未登录；404 会话不存在；500 更新失败
    ---
    tags:
      - 会话
    summary: 更新会话属性
    consumes:
      - application/json
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: session_id
        type: integer
        required: true
        description: 会话 ID
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - pinned
          properties:
            pinned:
              type: boolean
              description: 是否固定会话
    responses:
      200:
        description: 更新成功
      400:
        description: 缺少 pinned 参数
      401:
        description: 未登录
      404:
        description: 会话不存在或无权限
      500:
        description: 服务器内部错误
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401

    data = request.get_json(silent=True) or {}
    if 'pinned' not in data:
        return jsonify({'error': '缺少 pinned 参数'}), 400

    try:
        chat_service = ChatService(
            agent_service=get_agent_service(),
            llm_service=get_llm_service(),
            config=get_config(),
        )
        ok = chat_service.set_session_pinned(session_id, user['id'], bool(data['pinned']))
        if not ok:
            return jsonify({'error': '会话不存在或无权限'}), 404
        return jsonify({'success': True, 'is_pinned': bool(data['pinned'])})
    except Exception as e:
        print(f"Update session error: {e}")
        return jsonify({'error': '更新会话失败'}), 500


@chat_bp.route('/sessions/<int:session_id>', methods=['DELETE'])
def delete_session_route(session_id):
    """删除指定会话及其消息记录。

    用法:
    - 方法/路径: `DELETE /api/sessions/<session_id>`
    - 认证: Bearer Token
    - 成功响应: `{ "success": true }`
    - 失败响应: 401 未登录；404 会话不存在；500 删除失败
    ---
    tags:
      - 会话
    summary: 删除会话
    produces:
      - application/json
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: session_id
        type: integer
        required: true
        description: 会话 ID
    responses:
      200:
        description: 删除成功
      401:
        description: 未登录
      404:
        description: 会话不存在或无权限
      500:
        description: 服务器内部错误
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401

    try:
        chat_service = ChatService(
            agent_service=get_agent_service(),
            llm_service=get_llm_service(),
            config=get_config(),
        )
        ok = chat_service.delete_session(session_id, user['id'])
        if not ok:
            return jsonify({'error': '会话不存在或无权限'}), 404
        return jsonify({'success': True})
    except Exception as e:
        print(f"Delete session error: {e}")
        return jsonify({'error': '删除会话失败'}), 500


