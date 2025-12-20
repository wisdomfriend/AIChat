"""管理页面路由"""
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from ..utils import get_current_user, require_login, require_admin
from ..services import StatsService
from ..database import get_session
from ..models import ApiKey

# 创建蓝图
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@require_admin
def admin():
    """管理页面"""
    user = get_current_user()

    try:
        stats_service = StatsService()
        admin_data = stats_service.get_admin_stats()

        return render_template('admin.html',
                               user=user,
                               stats=admin_data['stats'],
                               recent_usage=admin_data['recent_usage'])
    except Exception as e:
        print(f"Admin error: {e}")
        flash('加载管理页面时出错', 'error')
        return redirect(url_for('dashboard.dashboard'))


