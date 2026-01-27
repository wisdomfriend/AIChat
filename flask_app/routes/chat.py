"""聊天相关路由"""
from flask import Blueprint, render_template, redirect, url_for, current_app
from ..utils import get_current_user, require_login

# 创建蓝图
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat')
@require_login
def chat():
    """聊天页面"""
    user = get_current_user()
    # 传递配置值到模板
    max_file_size = current_app.config.get('MAX_FILE_SIZE', 100 * 1024 * 1024)
    max_files_per_request = current_app.config.get('MAX_FILES_PER_REQUEST', 50)
    return render_template('chat.html', 
                         user=user, 
                         max_file_size=max_file_size,
                         max_files_per_request=max_files_per_request)

