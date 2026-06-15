"""认证页面路由。

页面总览（按用户使用流程）：
1) 入口
   - GET `/`  已登录跳转聊天页，未登录跳转登录页
2) 登录/注册
   - GET/POST `/login`  登录表单与提交（Session 认证）
   - GET/POST `/register`  注册表单与提交
3) 登出
   - GET `/logout`  清除 Session 并跳转登录页
"""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..services import AuthService
from ..utils import get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def index():
    """首页入口，按登录状态重定向。

    用法:
    - 方法/路径: `GET /`
    - 已登录: 302 跳转 `/chat`
    - 未登录: 302 跳转 `/login`
    """
    if get_current_user():
        return redirect(url_for('chat.chat'))
    return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录，成功后写入 Session。

    用法:
    - 方法/路径: `GET/POST /login`
    - GET: 渲染登录表单（已登录则跳转 `/chat`）
    - POST 表单字段: `username`、`password`
    - 成功: 302 跳转 `/chat`，Session 写入 `user_id`、`username`
    - 失败: 重新渲染表单并 flash 错误信息
    """
    if get_current_user():
        return redirect(url_for('chat.chat'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        auth_service = AuthService()
        result = auth_service.authenticate(username, password)

        if result['success']:
            session['user_id'] = result['user']['id']
            session['username'] = result['user']['username']
            session.permanent = True

            flash('登录成功！', 'success')
            return redirect(url_for('chat.chat'))
        else:
            flash(result['message'], 'error')

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册，成功后跳转登录页。

    用法:
    - 方法/路径: `GET/POST /register`
    - GET: 渲染注册表单（已登录则跳转 `/chat`）
    - POST 表单字段: `username`、`password`、`password_confirm`
    - 成功: 302 跳转 `/login`
    - 失败: 重新渲染表单并 flash 错误信息
    """
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
    """用户登出，清除 Session。

    用法:
    - 方法/路径: `GET /logout`
    - 成功: 清除 Session，302 跳转 `/login`
    """
    session.clear()
    flash('已成功登出！', 'info')
    return redirect(url_for('auth.login'))
