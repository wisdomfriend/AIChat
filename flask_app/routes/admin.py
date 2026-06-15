"""管理页面路由。

页面总览：
1) 管理后台
   - GET `/admin`  全局统计与最近 API 用量（需 admin）
"""
from flask import Blueprint, flash, redirect, render_template, url_for

from ..services import StatsService
from ..utils import get_current_user, require_admin

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@require_admin
def admin():
    """渲染管理后台页面，展示全局统计与最近用量。

    用法:
    - 方法/路径: `GET /admin`
    - 认证: Session Cookie，需 admin 权限
    - 模板变量: `user`、`stats`、`recent_usage`
    - 加载失败: flash 错误信息，302 跳转 `/dashboard`
    """
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
