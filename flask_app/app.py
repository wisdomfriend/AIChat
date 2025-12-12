from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, Boolean, text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
import os
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'guopengfei_learning_secret_key_2024'

# 启用CORS
CORS(app)

# 数据库配置
DATABASE_URL = f"mysql+pymysql://{os.environ.get('MYSQL_USER', 'guopengfei_learning')}:{os.environ.get('MYSQL_PASSWORD', 'Gpf_learning')}@{os.environ.get('MYSQL_HOST', 'mysql')}/{os.environ.get('MYSQL_DB', 'nginx_shop')}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 用户模型
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    last_login = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)

# API密钥配置模型
class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), nullable=False)
    provider = Column(String(50), default='deepseek')
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))

# Token使用记录模型
class TokenUsage(Base):
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    model = Column(String(50), default='deepseek-chat')
    request_time = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

# DeepSeek API配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 辅助函数：获取当前用户
def get_current_user():
    if 'user_id' in session:
        try:
            db = SessionLocal()
            user = db.query(User).filter(User.id == session['user_id']).first()
            db.close()
            if user and user.is_active:
                return {'id': user.id, 'username': user.username, 'last_login': user.last_login}
        except Exception as e:
            print(f"Get user error: {e}")
    return None

@app.route('/')
def index():
    if get_current_user():
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 如果已登录，直接跳转
    if get_current_user():
        return redirect(url_for('chat'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            db = SessionLocal()
            user = db.query(User).filter(User.username == username).first()

            if user and user.password == password and user.is_active:
                # 使用session存储用户信息
                session['user_id'] = user.id
                session['username'] = user.username

                # 更新最后登录时间
                user.last_login = datetime.utcnow()
                db.commit()
                db.close()

                flash('登录成功！', 'success')
                return redirect(url_for('chat'))
            else:
                flash('用户名或密码错误！', 'error')
                db.close()

        except Exception as e:
            flash('数据库连接错误，请稍后重试！', 'error')
            print(f"Database error: {e}")

    return render_template('login.html')

@app.route('/chat')
def chat():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    return render_template('chat.html', user=user)

@app.route('/dashboard')
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    try:
        db = SessionLocal()
        
        # 获取用户token使用统计
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        today_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
            TokenUsage.user_id == user['id'],
            func.date(TokenUsage.request_time) == today
        ).scalar() or 0
        
        week_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
            TokenUsage.user_id == user['id'],
            TokenUsage.request_time >= week_ago
        ).scalar() or 0
        
        month_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
            TokenUsage.user_id == user['id'],
            TokenUsage.request_time >= month_ago
        ).scalar() or 0
        
        total_usage = db.query(func.sum(TokenUsage.total_tokens)).filter(
            TokenUsage.user_id == user['id']
        ).scalar() or 0
        
        db.close()
        
        stats = {
            'today': today_usage,
            'week': week_usage,
            'month': month_usage,
            'total': total_usage
        }

        return render_template('dashboard.html', user=user, stats=stats)
    except Exception as e:
        print(f"Database error: {e}")
        return render_template('dashboard.html', user=user, stats={'today': 0, 'week': 0, 'month': 0, 'total': 0})

@app.route('/admin')
def admin():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    try:
        db = SessionLocal()
        
        # 获取当前API key
        api_key_obj = db.query(ApiKey).filter(ApiKey.is_active == True).first()
        current_api_key = api_key_obj.api_key if api_key_obj else ''
        
        # 获取token使用统计
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # 今日统计
        today_stats = db.query(
            func.sum(TokenUsage.prompt_tokens).label('prompt'),
            func.sum(TokenUsage.completion_tokens).label('completion'),
            func.sum(TokenUsage.total_tokens).label('total'),
            func.count(TokenUsage.id).label('count')
        ).filter(
            func.date(TokenUsage.request_time) == today
        ).first()
        
        # 本周统计
        week_stats = db.query(
            func.sum(TokenUsage.prompt_tokens).label('prompt'),
            func.sum(TokenUsage.completion_tokens).label('completion'),
            func.sum(TokenUsage.total_tokens).label('total'),
            func.count(TokenUsage.id).label('count')
        ).filter(
            TokenUsage.request_time >= week_ago
        ).first()
        
        # 本月统计
        month_stats = db.query(
            func.sum(TokenUsage.prompt_tokens).label('prompt'),
            func.sum(TokenUsage.completion_tokens).label('completion'),
            func.sum(TokenUsage.total_tokens).label('total'),
            func.count(TokenUsage.id).label('count')
        ).filter(
            TokenUsage.request_time >= month_ago
        ).first()
        
        # 总统计
        total_stats = db.query(
            func.sum(TokenUsage.prompt_tokens).label('prompt'),
            func.sum(TokenUsage.completion_tokens).label('completion'),
            func.sum(TokenUsage.total_tokens).label('total'),
            func.count(TokenUsage.id).label('count')
        ).first()
        
        # 最近10条使用记录
        recent_usage = db.query(TokenUsage).order_by(TokenUsage.request_time.desc()).limit(10).all()
        
        db.close()
        
        stats = {
            'today': {
                'prompt': today_stats.prompt or 0,
                'completion': today_stats.completion or 0,
                'total': today_stats.total or 0,
                'count': today_stats.count or 0
            },
            'week': {
                'prompt': week_stats.prompt or 0,
                'completion': week_stats.completion or 0,
                'total': week_stats.total or 0,
                'count': week_stats.count or 0
            },
            'month': {
                'prompt': month_stats.prompt or 0,
                'completion': month_stats.completion or 0,
                'total': month_stats.total or 0,
                'count': month_stats.count or 0
            },
            'total': {
                'prompt': total_stats.prompt or 0,
                'completion': total_stats.completion or 0,
                'total': total_stats.total or 0,
                'count': total_stats.count or 0
            }
        }
        
        return render_template('admin.html', 
                             user=user,
                             api_key=current_api_key,
                             stats=stats,
                             recent_usage=recent_usage)
    except Exception as e:
        print(f"Admin error: {e}")
        flash('加载管理页面时出错', 'error')
        return redirect(url_for('dashboard'))

@app.route('/admin/api_key', methods=['POST'])
def update_api_key():
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    try:
        data = request.get_json()
        new_api_key = data.get('api_key', '').strip()
        
        if not new_api_key:
            return jsonify({'success': False, 'message': 'API key不能为空'}), 400
        
        db = SessionLocal()
        
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

@app.route('/api/chat', methods=['POST'])
def api_chat():
    user = get_current_user()
    if not user:
        return jsonify({'error': '未登录'}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': '消息不能为空'}), 400
        
        db = SessionLocal()
        
        # 获取当前活跃的API key
        api_key_obj = db.query(ApiKey).filter(ApiKey.is_active == True).first()
        if not api_key_obj:
            db.close()
            return jsonify({'error': '未配置API key'}), 400
        
        api_key = api_key_obj.api_key
        
        # 调用DeepSeek API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'user', 'content': message}
            ],
            'stream': False
        }
        
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            db.close()
            return jsonify({'error': f'API调用失败: {response.text}'}), response.status_code
        
        result = response.json()
        
        # 提取token使用信息
        usage = result.get('usage', {})
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', 0)
        
        # 记录token使用
        token_usage = TokenUsage(
            user_id=user['id'],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model='deepseek-chat'
        )
        db.add(token_usage)
        db.commit()
        db.close()
        
        # 返回响应
        assistant_message = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        return jsonify({
            'success': True,
            'message': assistant_message,
            'usage': {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': total_tokens
            }
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'网络请求失败: {str(e)}'}), 500
    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({'error': f'处理请求时出错: {str(e)}'}), 500

@app.route('/logout')
def logout():
    session.clear()
    flash('已成功登出！', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
