"""API路由"""
import json
from flask import Blueprint, Response, request, stream_with_context, jsonify
from ..utils import get_current_user
from ..services import ChatService, FileService

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
        
        if not message:
            return Response(
                'data: {"type":"error","message":"消息不能为空"}\n\n',
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
                    file_ids
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


@api_bp.route('/sessions', methods=['POST'])
def create_session():
    """创建新会话"""
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json() or {}
        title = data.get('title')
        
        chat_service = ChatService()
        session_id = chat_service.create_session(user['id'], title)
        
        if session_id:
            return jsonify({'session_id': session_id})
        else:
            return jsonify({'error': '创建会话失败'}), 500
    except Exception as e:
        print(f"Create session error: {e}")
        return jsonify({'error': '创建会话失败'}), 500


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


@api_bp.route('/sessions/<int:session_id>/title', methods=['PUT'])
def update_session_title(session_id):
    """更新会话主题"""
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        
        if not title:
            return jsonify({'error': '主题不能为空'}), 400
        
        chat_service = ChatService()
        success = chat_service.update_session_title(session_id, user['id'], title)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': '更新失败'}), 404
    except Exception as e:
        print(f"Update session title error: {e}")
        return jsonify({'error': '更新失败'}), 500


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
