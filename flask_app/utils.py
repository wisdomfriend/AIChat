"""辅助工具函数"""
import os
import hashlib
from functools import wraps
from flask import session, redirect, url_for, flash, current_app
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


def get_static_file_hash(filename):
    """
    计算静态文件的哈希值并返回带哈希的文件名
    
    Args:
        filename: 静态文件路径，例如 'css/chat.css'
    
    Returns:
        带哈希的文件名，例如 'css/chat.a1b2c3d4.css'
        如果文件不存在，返回原始文件名
    """
    try:
        # 获取静态文件目录的绝对路径
        static_folder = current_app.static_folder
        file_path = os.path.join(static_folder, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return filename
        
        # 读取文件内容并计算 MD5 哈希
        with open(file_path, 'rb') as f:
            file_content = f.read()
            hash_value = hashlib.md5(file_content).hexdigest()[:8]  # 取前8位
        
        # 分离文件名和扩展名
        base_path, ext = os.path.splitext(filename)
        # 生成带哈希的文件名：css/chat.a1b2c3d4.css
        hashed_filename = f"{base_path}.{hash_value}{ext}"
        
        return hashed_filename
    except Exception as e:
        # 如果出错，返回原始文件名
        print(f"计算文件哈希失败: {e}")
        return filename

