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
                               api_key=admin_data['api_key'],
                               stats=admin_data['stats'],
                               recent_usage=admin_data['recent_usage'])
    except Exception as e:
        print(f"Admin error: {e}")
        flash('加载管理页面时出错', 'error')
        return redirect(url_for('dashboard.dashboard'))


@admin_bp.route('/admin/api_key', methods=['POST'])
@require_admin
def update_api_key():
    """更新API key"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401
    if not user.get('is_admin', False):
        return jsonify({'success': False, 'message': '权限不足'}), 403

    try:
        data = request.get_json()
        new_api_key = data.get('api_key', '').strip()

        if not new_api_key:
            return jsonify({'success': False, 'message': 'API key不能为空'}), 400

        db = get_session()

        # 将现有key设为非活跃
        db.query(ApiKey).update({ApiKey.is_active: False})

        # 创建新的API key记录
        api_key = ApiKey(api_key=new_api_key, provider='deepseek', is_active=True)
        db.add(api_key)
        db.commit()
        db.close()

        return jsonify({'success': True, 'message': 'API key更新成功'})
    except Exception as e:
        print(f"Update API key error: {e}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500
