"""辅助工具函数"""
from functools import wraps
from flask import session, redirect, url_for, flash
from .database import get_session
from .models import User


def get_current_user():
    """获取当前登录用户"""
    if 'user_id' not in session:
        return None
    
    try:
        db = get_session()
        user = db.query(User).filter(User.id == session['user_id']).first()
        db.close()
        
        if user and user.is_active:
            return {
                'id': user.id,
                'username': user.username,
                'last_login': user.last_login,
                'is_admin': user.is_admin if hasattr(user, 'is_admin') else False
            }
    except Exception as e:
        print(f"Get user error: {e}")
    
    return None


def require_login(f):
    """装饰器：要求用户登录"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            flash('请先登录后再访问', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """装饰器：要求用户是管理员"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('请先登录后再访问', 'warning')
            return redirect(url_for('auth.login'))
        if not user.get('is_admin', False):
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('chat.chat'))
        return f(*args, **kwargs)
    return decorated_function

