"""仪表板页面路由。

页面总览：
1) 统计
   - GET `/dashboard`  用户 Token 使用统计（需 admin）
"""
from flask import Blueprint, redirect, render_template, url_for

from ..services import StatsService
from ..utils import get_current_user, require_admin

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@require_admin
def dashboard():
    """渲染用户 Token 使用统计仪表板。

    用法:
    - 方法/路径: `GET /dashboard`
    - 认证: Session Cookie，需 admin 权限
    - 未登录: 302 跳转 `/login`
    - 非 admin: 302 跳转 `/chat`
    - 模板变量: `user`、`stats`（今日/本周/本月 Token 用量）
    """
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    stats_service = StatsService()
    stats = stats_service.get_user_stats(user['id'])

    return render_template('dashboard.html', user=user, stats=stats)
