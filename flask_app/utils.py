"""辅助工具函数"""
from flask import session
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
    from functools import wraps
    from flask import redirect, url_for
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """装饰器：要求用户是管理员"""
    from functools import wraps
    from flask import redirect, url_for, flash
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for('auth.login'))
        if not user.get('is_admin', False):
            flash('您没有权限访问此页面', 'error')
            return redirect(url_for('dashboard.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

