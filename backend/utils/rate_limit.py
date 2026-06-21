"""聊天 API Redis 限流工具。"""
import json
import time
import uuid
from functools import wraps
from typing import Tuple

from flask import Response

from backend.utils.user import get_current_user


class RedisRateLimiter:
    """基于 Redis sorted set 的多层级滑动窗口限流器。"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.limits = [
            (60, 6, "1分钟内最多6次"),
            (86400, 100, "1天"),
            (604800, 300, "1周"),
        ]
        self.key_prefix = "rate_limit:chat:"

    def _get_redis_client(self):
        if self.redis_client:
            return self.redis_client

        try:
            from backend.config import get_config

            return get_config().REDIS_CLIENT
        except Exception:
            pass

        return None

    def _check_single_limit(
        self, user_id: int, window_seconds: int, max_requests: int
    ) -> Tuple[bool, float]:
        redis_client = self._get_redis_client()
        if not redis_client:
            return True, 0.0

        try:
            current_time = time.time()
            key = f"{self.key_prefix}{user_id}:{window_seconds}"

            pipe = redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, current_time - window_seconds)
            pipe.zcard(key)
            results = pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                oldest_times = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_times:
                    oldest_time = oldest_times[0][1]
                    next_allowed_time = oldest_time + window_seconds
                    remaining_seconds = max(0, next_allowed_time - current_time)
                    return False, remaining_seconds
                return False, window_seconds

            member = f"{user_id}:{current_time}:{uuid.uuid4().hex[:8]}"
            redis_client.zadd(key, {member: current_time})
            redis_client.expire(key, window_seconds + 60)
            return True, 0.0

        except Exception as e:
            print(f"Redis限流检查失败: {e}")
            return True, 0.0

    def is_allowed(self, user_id: int) -> Tuple[bool, str, float]:
        for window_seconds, max_requests, description in self.limits:
            is_allowed, remaining_seconds = self._check_single_limit(
                user_id, window_seconds, max_requests
            )
            if not is_allowed:
                return False, description, remaining_seconds

        return True, "", 0.0


chat_rate_limiter = RedisRateLimiter()


def rate_limit_chat(f):
    """聊天 API 装饰器：按用户 ID 多层级限流。"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return f(*args, **kwargs)

        user_id = user["id"]
        is_allowed, limit_description, remaining_seconds = chat_rate_limiter.is_allowed(user_id)

        if not is_allowed:
            remaining_seconds_int = int(remaining_seconds) + 1

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

            error_message = (
                f"访问过于频繁，已达到{limit_description}的访问限制。"
                f"请稍后再试，您可以在 {time_str} 后再次访问。"
            )

            return Response(
                f'data: {json.dumps({"type": "error", "message": error_message})}\n\n',
                mimetype="text/event-stream",
                status=429,
            )

        return f(*args, **kwargs)

    return decorated_function
