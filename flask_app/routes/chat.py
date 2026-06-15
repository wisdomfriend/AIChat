"""聊天页面路由。

页面总览：
1) 聊天
   - GET `/chat`  聊天主界面（需登录）
"""
from flask import Blueprint, current_app, render_template

from ..services import ChatService
from ..utils import get_current_user, require_login

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chat')
@require_login
def chat():
    """渲染聊天页面，注入会话与上传配置。

    用法:
    - 方法/路径: `GET /chat`
    - 认证: Session Cookie（未登录跳转 `/login`）
    - 模板变量:
      - `user`  当前用户信息
      - `initial_session_id`  最近非空会话 ID（无则 null）
      - `max_file_size`  单文件大小上限（字节）
      - `max_files_per_request`  单次请求最大文件数
    """
    user = get_current_user()
    chat_service = ChatService()
    initial_session_id = chat_service.get_latest_session_id(user['id'], prefer_non_empty=True)
    max_file_size = current_app.config.get('MAX_FILE_SIZE', 100 * 1024 * 1024)
    max_files_per_request = current_app.config.get('MAX_FILES_PER_REQUEST', 50)
    return render_template('chat.html',
                         user=user,
                         max_file_size=max_file_size,
                         max_files_per_request=max_files_per_request,
                         initial_session_id=initial_session_id)
