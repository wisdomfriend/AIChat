"""API路由"""
from flask import Blueprint, jsonify, request
from ..utils import get_current_user
from ..services import ChatService

# 创建蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/chat', methods=['POST'])
def api_chat():
    """聊天API"""
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
        
        chat_service = ChatService()
        result = chat_service.process_chat(user['id'], message)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify({'error': result['error']}), 400
            
    except Exception as e:
        print(f"Chat API error: {e}")
        return jsonify({'error': f'处理请求时出错: {str(e)}'}), 500

