"""API路由"""
import json
from flask import Blueprint, Response, request, stream_with_context, jsonify
from ..utils import get_current_user
from ..services import ChatService, FileService, LLMService
from ..config import Config

# 创建蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/chat', methods=['POST'])
def api_chat():
    """流式聊天API (SSE) - 支持会话和文件"""
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
        use_web_search = data.get('use_web_search', False)  # 是否启用联网搜索
        
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
                    use_web_search
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
    """获取用户的会话列表"""
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
    """获取会话的所有消息"""
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
    """上传文件"""
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
    """获取用户的文件列表"""
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
    """获取文件信息"""
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
    """删除文件"""
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


@api_bp.route('/files/supported', methods=['GET'])
def get_supported_extensions():
    """获取支持的文件类型"""
    from ..services.file_service import FileExtractor
    extractor = FileExtractor()
    return jsonify({
        'extensions': extractor.get_supported_extensions(),
        'max_size_mb': 100
    })


# ==================== LLM 模型相关 API ====================

@api_bp.route('/llm/providers', methods=['GET'])
def get_llm_providers():
    """获取可用的 LLM 模型提供商列表"""
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
