"""认证相关路由"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..utils import get_current_user, require_login
from ..services import AuthService

# 创建蓝图
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """首页路由"""
    if get_current_user():
        return redirect(url_for('chat.chat'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录路由"""
    # 如果已登录，直接跳转
    if get_current_user():
        return redirect(url_for('chat.chat'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        auth_service = AuthService()
        result = auth_service.authenticate(username, password)
        
        if result['success']:
            # 使用session存储用户信息
            session['user_id'] = result['user']['id']
            session['username'] = result['user']['username']
            # 设置Session为永久，使用配置的过期时间（默认7天）
            session.permanent = True
            
            flash('登录成功！', 'success')
            return redirect(url_for('chat.chat'))
        else:
            flash(result['message'], 'error')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册路由"""
    # 如果已登录，直接跳转
    if get_current_user():
        return redirect(url_for('chat.chat'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        auth_service = AuthService()
        result = auth_service.register(username, password, password_confirm)
        
        if result['success']:
            flash('注册成功！请登录', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(result['message'], 'error')
    
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """登出路由"""
    session.clear()
    flash('已成功登出！', 'info')
    return redirect(url_for('auth.login'))

