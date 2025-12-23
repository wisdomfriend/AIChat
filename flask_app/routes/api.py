"""API路由"""
import json
import os
from flask import Blueprint, Response, request, stream_with_context, jsonify, send_file
from ..utils import get_current_user
from ..services import ChatService, FileService, LLMService
from ..config import Config
from ..database import get_session
from ..models import UploadedFile

# 创建蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/test-auth', methods=['GET'])
def test_auth():
    """
    测试认证状态
    ---
    tags:
      - 聊天
    summary: 测试当前用户的认证状态
    description: 用于调试，检查当前请求是否包含有效的 Session Cookie
    produces:
      - application/json
    responses:
      200:
        description: 认证状态
        schema:
          type: object
          properties:
            authenticated:
              type: boolean
              description: 是否已认证
            user:
              type: object
              description: 用户信息（如果已认证）
            cookies:
              type: object
              description: 请求中的 Cookie 信息
    """
    from flask import session as flask_session, current_app
    from ..config import Config
    
    try:
        user = get_current_user()
        cookies_info = {k: v[:50] + '...' if len(str(v)) > 50 else v for k, v in request.cookies.items()}
        
        # 获取详细的 Session 信息
        config = Config()
        # 使用 current_app 而不是 request.application，更安全
        session_cookie_name = current_app.config.get('SESSION_COOKIE_NAME', 'session')
        session_cookie_value = request.cookies.get(session_cookie_name)
        
        # 检查 Session 内容
        session_data = dict(flask_session) if flask_session else {}
        session_user_id = session_data.get('user_id')
        
        # 检查 Redis 中的 Session（如果使用 Redis）
        redis_session_info = None
        if current_app.config.get('SESSION_REDIS'):
            try:
                redis_client = current_app.config.get('SESSION_REDIS')
                key_prefix = current_app.config.get('SESSION_KEY_PREFIX', 'session:')
                
                # 尝试从 Cookie 值读取（可能需要签名验证）
                if session_cookie_value:
                    # 如果使用签名器，需要先验证签名
                    # 直接使用 Flask 应用已配置的签名器（如果存在）
                    session_interface = getattr(current_app, 'session_interface', None)
                    if session_interface and hasattr(session_interface, 'signer') and session_interface.signer is not None:
                        try:
                            # 使用 Flask-Session 的签名器（通常是 itsdangerous.Signer 或 TimestampSigner）
                            max_age = getattr(session_interface, 'permanent_session_lifetime', None) or current_app.permanent_session_lifetime
                            unsigned_sid = session_interface.signer.unsign(session_cookie_value, max_age=max_age)
                            # 确保是字符串类型
                            if isinstance(unsigned_sid, bytes):
                                unsigned_sid = unsigned_sid.decode('utf-8')
                            redis_key = key_prefix + str(unsigned_sid)
                        except Exception as e:
                            # 签名验证失败，尝试直接使用原始值（可能是未签名的旧Cookie）
                            redis_key = key_prefix + session_cookie_value
                            redis_session_info = {'warning': f'签名验证失败，使用原始值: {str(e)}', 'raw_cookie': session_cookie_value[:50]}
                    else:
                        # 没有使用签名器，直接使用 Cookie 值
                        redis_key = key_prefix + session_cookie_value
                    
                    if 'error' not in (redis_session_info or {}):
                        redis_val = redis_client.get(redis_key)
                        if redis_val:
                            redis_session_info = {
                                'found': True,
                                'key': redis_key,
                                'data_length': len(redis_val)
                            }
                        else:
                            redis_session_info = {
                                'found': False,
                                'key': redis_key,
                                'message': 'Redis 中未找到对应的 Session 数据'
                            }
            except Exception as e:
                redis_session_info = {'error': str(e)}
        
        return jsonify({
            'authenticated': user is not None,
            'user': user if user else None,
            'cookies': cookies_info,
            'session_cookie_name': session_cookie_name,
            'session_cookie_value': session_cookie_value[:100] + '...' if session_cookie_value and len(session_cookie_value) > 100 else session_cookie_value,
            'session_data': session_data,
            'session_user_id': session_user_id,
            'redis_session_info': redis_session_info,
            'session_use_signer': current_app.config.get('SESSION_USE_SIGNER', False),
            'session_key_prefix': current_app.config.get('SESSION_KEY_PREFIX', 'session:')
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': '服务器内部错误',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@api_bp.route('/chat', methods=['POST'])
def api_chat():
    """
    流式聊天API (SSE) - 支持会话和文件
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
            agent_mode:
              type: string
              description: Agent 模式，可选值：normal（普通聊天）、web_search（联网搜索）、react（推理与行动）、plan_execute（规划与执行）
              default: "normal"
              example: "react"
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return Response(
            'data: {"type":"error","message":"未登录"}\n\n',
            mimetype='text/event-stream',
            status=401
        )
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id')  # 会话ID，如果为None则创建新会话
        file_ids = data.get('file_ids', [])  # 附加的文件ID列表
        llm_provider = data.get('llm_provider')  # 模型提供商ID（可选）
        agent_mode = data.get('agent_mode', 'normal')  # Agent 模式
        
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
        
        chat_service = ChatService()
        
        def generate():
            """生成SSE流"""
            try:
                for chunk in chat_service.process_chat_stream_with_session(
                    user['id'], 
                    session_id, 
                    message,
                    file_ids,
                    llm_provider,
                    agent_mode
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


@api_bp.route('/sessions', methods=['GET'])
def get_sessions():
    """
    获取用户的会话列表
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        chat_service = ChatService()
        sessions = chat_service.get_sessions(user['id'])
        return jsonify({'sessions': sessions})
    except Exception as e:
        print(f"Get sessions error: {e}")
        return jsonify({'error': '获取会话列表失败'}), 500


@api_bp.route('/sessions/<int:session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """
    获取会话的所有消息
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        chat_service = ChatService()
        # 包含文件信息
        messages = chat_service.get_session_messages(session_id, user['id'], include_files=True)
        
        if messages is None:
            return jsonify({'error': '会话不存在或无权限'}), 404
        
        return jsonify({'messages': messages})
    except Exception as e:
        print(f"Get session messages error: {e}")
        return jsonify({'error': '获取消息失败'}), 500


# ==================== 文件相关 API ====================

@api_bp.route('/files', methods=['POST'])
def upload_file():
    """
    上传文件
    ---
    tags:
      - 文件
    summary: 上传文件
    description: |
      上传文件到服务器，支持 PDF、DOCX、XLSX、TXT 等格式。
      文件大小限制：100MB
      上传成功后返回文件ID，可用于聊天时附加文件。
    consumes:
      - multipart/form-data
    produces:
      - application/json
    parameters:
      - in: formData
        name: file
        type: file
        required: true
        description: 要上传的文件
    responses:
      200:
        description: 上传成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            file_id:
              type: integer
              description: 文件ID
              example: 1
            filename:
              type: string
              description: 文件名
              example: "document.pdf"
            file_type:
              type: string
              description: 文件类型
              example: "pdf"
            file_size:
              type: integer
              description: 文件大小（字节）
              example: 1024000
            message:
              type: string
              example: "文件上传成功"
        examples:
          application/json:
            success: true
            file_id: 1
            filename: "document.pdf"
            file_type: "pdf"
            file_size: 1024000
            message: "文件上传成功"
      400:
        description: 请求参数错误
        schema:
          type: object
          properties:
            error:
              type: string
              example: "没有上传文件"
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
        
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': '文件名为空'}), 400
        
        file_service = FileService()
        result = file_service.save_file(user['id'], file)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Upload file error: {e}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500


@api_bp.route('/files', methods=['GET'])
def get_files():
    """
    获取用户的文件列表
    ---
    tags:
      - 文件
    summary: 获取当前用户的所有文件
    description: 返回当前登录用户上传的所有文件列表
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            files:
              type: array
              items:
                type: object
                properties:
                  id:
                    type: integer
                    description: 文件ID
                    example: 1
                  filename:
                    type: string
                    description: 文件名
                    example: "document.pdf"
                  file_type:
                    type: string
                    description: 文件类型
                    example: "pdf"
                  file_size:
                    type: integer
                    description: 文件大小（字节）
                    example: 1024000
                  created_at:
                    type: string
                    format: date-time
                    description: 上传时间
                    example: "2024-01-01T12:00:00"
        examples:
          application/json:
            files:
              - id: 1
                filename: "document.pdf"
                file_type: "pdf"
                file_size: 1024000
                created_at: "2024-01-01T12:00:00"
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        file_service = FileService()
        files = file_service.get_user_files(user['id'])
        return jsonify({'files': files})
    except Exception as e:
        print(f"Get files error: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500


@api_bp.route('/files/<int:file_id>', methods=['GET'])
def get_file(file_id):
    """
    获取文件信息
    ---
    tags:
      - 文件
    summary: 获取指定文件的详细信息
    description: 返回指定文件的详细信息，包括文件内容摘要等
    produces:
      - application/json
    parameters:
      - in: path
        name: file_id
        type: integer
        required: true
        description: 文件ID
        example: 1
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            id:
              type: integer
              description: 文件ID
              example: 1
            filename:
              type: string
              description: 文件名
              example: "document.pdf"
            file_type:
              type: string
              description: 文件类型
              example: "pdf"
            file_size:
              type: integer
              description: 文件大小（字节）
              example: 1024000
            created_at:
              type: string
              format: date-time
              description: 上传时间
              example: "2024-01-01T12:00:00"
            content_preview:
              type: string
              description: 文件内容预览
              example: "这是文件的前500个字符..."
      401:
        description: 未登录
        schema:
          type: object
          properties:
            error:
              type: string
              example: "未登录"
      404:
        description: 文件不存在或无权限
        schema:
          type: object
          properties:
            error:
              type: string
              example: "文件不存在或无权限"
      500:
        description: 服务器内部错误
    security:
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        file_service = FileService()
        file_info = file_service.get_file(file_id, user['id'])
        
        if not file_info:
            return jsonify({'error': '文件不存在或无权限'}), 404
        
        return jsonify(file_info)
    except Exception as e:
        print(f"Get file error: {e}")
        return jsonify({'error': '获取文件信息失败'}), 500


@api_bp.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    删除文件
    ---
    tags:
      - 文件
    summary: 删除指定文件
    description: 删除用户上传的指定文件，只能删除自己的文件
    produces:
      - application/json
    parameters:
      - in: path
        name: file_id
        type: integer
        required: true
        description: 文件ID
        example: 1
    responses:
      200:
        description: 删除成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
        examples:
          application/json:
            success: true
      400:
        description: 删除失败
        schema:
          type: object
          properties:
            error:
              type: string
              example: "文件不存在或无权限"
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        file_service = FileService()
        result = file_service.delete_file(file_id, user['id'])
        
        if result['success']:
            return jsonify({'success': True})
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Delete file error: {e}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500


@api_bp.route('/files/<int:file_id>/image', methods=['GET'])
def get_image(file_id):
    """
    获取图片文件
    ---
    tags:
      - 文件
    summary: 获取图片文件内容
    description: 返回图片文件的二进制内容，需要登录验证
    produces:
      - image/*
    parameters:
      - in: path
        name: file_id
        type: integer
        required: true
        description: 文件ID
        example: 1
    responses:
      200:
        description: 图片文件
        schema:
          type: file
      401:
        description: 未登录
      404:
        description: 文件不存在、无权限或不是图片文件
      500:
        description: 服务器内部错误
    security:
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    db = get_session()
    try:
        file_obj = db.query(UploadedFile).filter(
            UploadedFile.id == file_id,
            UploadedFile.user_id == user['id']
        ).first()
        
        if not file_obj:
            return jsonify({'error': '文件不存在或无权限'}), 404
        
        # 检查是否为图片文件
        file_service = FileService()
        if not file_service.extractor.is_image(file_obj.file_extension):
            return jsonify({'error': '文件不是图片格式'}), 404
        
        # 检查文件是否存在
        if not os.path.exists(file_obj.file_path):
            return jsonify({'error': '文件不存在'}), 404
        
        # 返回图片文件
        return send_file(
            file_obj.file_path,
            mimetype=file_obj.file_type or 'image/jpeg',
            as_attachment=False
        )
    except Exception as e:
        print(f"Get image error: {e}")
        return jsonify({'error': '获取图片失败'}), 500
    finally:
        db.close()


@api_bp.route('/files/supported', methods=['GET'])
def get_supported_extensions():
    """
    获取支持的文件类型
    ---
    tags:
      - 文件
    summary: 获取支持的文件类型列表
    description: 返回系统支持上传的文件类型和大小限制
    produces:
      - application/json
    responses:
      200:
        description: 获取成功
        schema:
          type: object
          properties:
            extensions:
              type: array
              items:
                type: string
              description: 支持的文件扩展名列表
              example: ["pdf", "docx", "xlsx", "txt", "py", "js", "html", "css"]
            max_size_mb:
              type: integer
              description: 最大文件大小（MB）
              example: 100
        examples:
          application/json:
            extensions: ["pdf", "docx", "xlsx", "txt", "py", "js", "html", "css"]
            max_size_mb: 100
    """
    from ..services.file_service import FileExtractor
    extractor = FileExtractor()
    return jsonify({
        'extensions': extractor.get_supported_extensions(),
        'max_size_mb': 100
    })


# ==================== LLM 模型相关 API ====================

@api_bp.route('/llm/providers', methods=['GET'])
def get_llm_providers():
    """
    获取可用的 LLM 模型提供商列表
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
      - sessionAuth: []
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        config = Config()
        llm_service = LLMService(config)
        providers = llm_service.get_available_providers()
        
        return jsonify({
            'providers': providers,
            'default': config.LLM_DEFAULT_PROVIDER
        })
    except Exception as e:
        print(f"Get LLM providers error: {e}")
        return jsonify({'error': '获取模型列表失败'}), 500
