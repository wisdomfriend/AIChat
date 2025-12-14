"""API路由"""
import json
from flask import Blueprint, Response, request, stream_with_context
from ..utils import get_current_user
from ..services import ChatService

# 创建蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/chat', methods=['POST'])
def api_chat():
    """流式聊天API (SSE)"""
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
                for chunk in chat_service.process_chat_stream(user['id'], message):
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

