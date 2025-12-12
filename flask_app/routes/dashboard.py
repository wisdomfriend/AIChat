"""仪表板路由"""
from flask import Blueprint, render_template, redirect, url_for
from ..utils import get_current_user, require_login
from ..services import StatsService

# 创建蓝图
dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@require_login
def dashboard():
    """仪表板页面"""
    user = get_current_user()
    if not user:
        return redirect(url_for('auth.login'))
    
    stats_service = StatsService()
    stats = stats_service.get_user_stats(user['id'])
    
    return render_template('dashboard.html', user=user, stats=stats)

