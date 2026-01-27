"""辅助工具函数"""
import os
import hashlib
import time
import uuid
from functools import wraps
from typing import Tuple
from flask import session, redirect, url_for, flash, current_app, Response
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


class RedisRateLimiter:
    """
    基于Redis的多层级访问频率限制器
    支持多进程环境，使用Redis sorted set实现滑动窗口
    """
    def __init__(self, redis_client=None):
        """
        初始化限流器
        
        Args:
            redis_client: Redis客户端实例，如果为None则从Flask应用配置中获取
        """
        self.redis_client = redis_client
        # 限流规则配置：[(时间窗口秒数, 最大请求数, 描述), ...]
        self.limits = [
            (60, 6, "1分钟内最多6次"),           # 1分钟内最多6次
            (86400, 100, "1天"),        # 1天内最多100次 (24*60*60 = 86400秒)
            (604800, 300, "1周")        # 1周内最多300次 (7*24*60*60 = 604800秒)
        ]
        self.key_prefix = "rate_limit:chat:"  # Redis键前缀
    
    def _get_redis_client(self):
        """获取Redis客户端"""
        if self.redis_client:
            return self.redis_client
        
        # 尝试从Flask应用配置中获取
        try:
            from flask import current_app
            redis_client = current_app.config.get('SESSION_REDIS')
            if redis_client:
                return redis_client
        except Exception:
            pass
        
        # 如果都获取不到，返回None（将使用内存回退）
        return None
    
    def _check_single_limit(self, user_id: int, window_seconds: int, max_requests: int) -> Tuple[bool, float]:
        """
        检查单个限流规则
        
        Args:
            user_id: 用户ID
            window_seconds: 时间窗口（秒）
            max_requests: 最大请求数
        
        Returns:
            (是否允许, 距离下次允许访问的剩余秒数)
        """
        redis_client = self._get_redis_client()
        if not redis_client:
            # 如果没有Redis，返回允许（降级处理）
            return True, 0.0
        
        try:
            current_time = time.time()
            key = f"{self.key_prefix}{user_id}:{window_seconds}"
            
            # 使用Redis pipeline提高性能
            pipe = redis_client.pipeline()
            
            # 1. 移除超出时间窗口的旧记录
            pipe.zremrangebyscore(key, 0, current_time - window_seconds)
            
            # 2. 获取当前窗口内的请求数
            pipe.zcard(key)
            
            # 3. 执行pipeline
            results = pipe.execute()
            current_count = results[1]
            
            # 4. 检查是否超过限制
            if current_count >= max_requests:
                # 获取最早请求的时间戳
                oldest_times = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_times:
                    oldest_time = oldest_times[0][1]
                    next_allowed_time = oldest_time + window_seconds
                    remaining_seconds = max(0, next_allowed_time - current_time)
                    return False, remaining_seconds
                else:
                    # 理论上不应该到这里，但为了安全起见
                    return False, window_seconds
            
            # 5. 允许访问，记录当前请求时间
            # 使用当前时间戳作为score，用户ID+时间戳+UUID作为member（确保唯一性）
            member = f"{user_id}:{current_time}:{uuid.uuid4().hex[:8]}"  # 使用UUID确保唯一性
            redis_client.zadd(key, {member: current_time})
            
            # 6. 设置key的过期时间（窗口时间 + 60秒缓冲，确保数据清理）
            redis_client.expire(key, window_seconds + 60)
            
            return True, 0.0
            
        except Exception as e:
            # Redis操作失败时，记录错误但不阻止请求（降级处理）
            print(f"Redis限流检查失败: {e}")
            return True, 0.0
    
    def is_allowed(self, user_id: int) -> Tuple[bool, str, float]:
        """
        检查用户是否允许访问（检查所有限流规则）
        
        Args:
            user_id: 用户ID
        
        Returns:
            (是否允许, 错误描述, 距离下次允许访问的剩余秒数)
            如果允许访问，错误描述为空字符串，剩余秒数为 0
        """
        for window_seconds, max_requests, description in self.limits:
            is_allowed, remaining_seconds = self._check_single_limit(user_id, window_seconds, max_requests)
            if not is_allowed:
                return False, description, remaining_seconds
        
        return True, "", 0.0


# 创建全局限流器实例（Redis客户端将在使用时从Flask应用获取）
chat_rate_limiter = RedisRateLimiter()


def rate_limit_chat(f):
    """
    装饰器：限制聊天 API 的访问频率
    多层级限流规则：
    - 1 分钟内最多 6 次
    - 1 天内最多 100 次
    - 1 周内最多 300 次
    基于用户 ID 进行限流，支持多进程环境
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            # 未登录用户不受限流影响，由其他装饰器处理
            return f(*args, **kwargs)
        
        user_id = user['id']
        is_allowed, limit_description, remaining_seconds = chat_rate_limiter.is_allowed(user_id)
        
        if not is_allowed:
            # 返回友好的错误提示
            import json
            remaining_seconds_int = int(remaining_seconds) + 1  # 向上取整，更友好
            
            # 根据剩余时间生成友好的提示
            if remaining_seconds_int < 60:
                time_str = f"{remaining_seconds_int} 秒"
            elif remaining_seconds_int < 3600:
                minutes = remaining_seconds_int // 60
                time_str = f"{minutes} 分钟"
            elif remaining_seconds_int < 86400:
                hours = remaining_seconds_int // 3600
                time_str = f"{hours} 小时"
            else:
                days = remaining_seconds_int // 86400
                time_str = f"{days} 天"
            
            error_message = f"访问过于频繁，已达到{limit_description}的访问限制。请稍后再试，您可以在 {time_str} 后再次访问。"
            
            return Response(
                f'data: {json.dumps({"type": "error", "message": error_message})}\n\n',
                mimetype='text/event-stream',
                status=429  # 429 Too Many Requests
            )
        
        return f(*args, **kwargs)
    
    return decorated_function

