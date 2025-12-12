"""聊天相关路由"""
from flask import Blueprint, render_template, redirect, url_for
from ..utils import get_current_user, require_login

# 创建蓝图
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat')
@require_login
def chat():
    """聊天页面"""
    user = get_current_user()
    return render_template('chat.html', user=user)

