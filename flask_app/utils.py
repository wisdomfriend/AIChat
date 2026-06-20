"""通用工具函数与装饰器。

职责总览：
1) 用户与权限
   - `get_current_user()`  从 Bearer Token 读取当前用户
   - `serialize_user()`    用户 dict 序列化
2) 限流
   - `RedisRateLimiter`  基于 Redis 的多层级滑动窗口限流
   - `rate_limit_chat`   聊天 API 限流装饰器
"""
import time
import uuid
from functools import wraps
from typing import Tuple

from flask import Response, request

from .database import get_session
from .models import User
from .services.auth_token import get_bearer_token, verify_user_token


def get_client_ip() -> str:
    """从代理头或 remote_addr 提取客户端 IP。"""
    forwarded = request.headers.get("X-Forwarded-For", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP", "").strip()
    if real_ip:
        return real_ip
    return request.remote_addr or "unknown"


def serialize_user(user: dict | None) -> dict | None:
    """将用户 dict 序列化为 API 响应格式。

    用法:
    - 调用方: `routes/auth_api`、`/api/*` 返回用户信息
    - 参数: `user` — `{ id, username, last_login, is_admin }`
    - 返回值: JSON 可序列化 dict；`user` 为 None 时返回 None
    """
    if not user:
        return None
    last_login = user.get("last_login")
    if last_login is not None and hasattr(last_login, "isoformat"):
        last_login = last_login.isoformat()
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "last_login": last_login,
        "is_admin": bool(user.get("is_admin", False)),
    }


def _user_row_to_dict(user: User) -> dict:
    """将 ORM User 转为 API 内部使用的用户 dict（内部使用）。

    用法:
    - 调用方: `get_current_user()`
    - 返回值: `{ id, username, last_login, is_admin }`
    """
    return {
        "id": user.id,
        "username": user.username,
        "last_login": user.last_login,
        "is_admin": bool(user.is_admin) if hasattr(user, "is_admin") else False,
    }


def get_current_user():
    """从 Bearer Token 读取当前登录用户。

    用法:
    - 请求头: `Authorization: Bearer <token>`
    - 返回值: `{ id, username, last_login, is_admin }` 或 None
    """
    token = get_bearer_token()
    if not token:
        return None

    payload = verify_user_token(token)
    if not payload:
        return None

    try:
        db = get_session()
        user = db.query(User).filter(User.id == payload["user_id"]).first()
        db.close()

        if user and user.is_active:
            return _user_row_to_dict(user)
    except Exception as e:
        print(f"Get user error: {e}")

    return None


class RedisRateLimiter:
    """基于 Redis sorted set 的多层级滑动窗口限流器。

    用法:
    - 调用方: `rate_limit_chat` 装饰器
    - 规则: 1 分钟 6 次 / 1 天 100 次 / 1 周 300 次
    - Redis 不可用: 降级放行（不阻断请求）
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
            redis_client = current_app.config.get('REDIS_CLIENT')
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
    """聊天 API 装饰器：按用户 ID 多层级限流。

    用法:
    - 装饰目标: `POST /api/chat`
    - 超限: 返回 SSE 429，`{ "type": "error", "message": "..." }`
    - 未登录: 不限流，由路由层处理 401
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

