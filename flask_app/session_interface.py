"""自定义 Redis Session 接口，修复 session_id bytes 类型问题。

职责总览：
1) Session ID 规范化
   - `_ensure_string_sid()`  将 bytes 转为 str
2) Session 读写
   - `save_session()`  保存 Session 到 Redis 并设置 Cookie
   - `open_session()`   从 Cookie/Redis 恢复 Session
"""
import base64
import logging

from flask_session.sessions import RedisSessionInterface

logger = logging.getLogger(__name__)


class FixedRedisSessionInterface(RedisSessionInterface):
    """修复 Flask-Session Redis 接口中 session_id 为 bytes 导致的 Cookie 写入异常。"""
    
    def _ensure_string_sid(self, session_id):
        """确保session_id是字符串类型"""
        if session_id is None:
            return None
        
        if isinstance(session_id, bytes):
            # 如果是bytes，尝试解码为字符串
            try:
                return session_id.decode('utf-8')
            except (UnicodeDecodeError, AttributeError):
                # 如果解码失败，使用base64编码
                return base64.urlsafe_b64encode(session_id).decode('utf-8').rstrip('=')
        
        # 确保是字符串
        if not isinstance(session_id, str):
            return str(session_id)
        
        return session_id
    
    def _save_session_custom(self, app, session, response):
        """自定义保存session实现（当父类方法失败时使用）"""
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        
        # 如果session为None，直接返回
        if session is None:
            return
        
        # 如果session为空且被修改过，删除cookie
        if not session:
            if hasattr(session, 'modified') and session.modified:
                response.delete_cookie(
                    app.config["SESSION_COOKIE_NAME"],
                    domain=domain,
                    path=path
                )
            return
        
        # 获取或生成session_id
        if not hasattr(session, 'sid') or session.sid is None:
            session_id = self._generate_sid()
            if hasattr(self, 'signer') and self.signer is not None:
                session_id = self.signer.sign(session_id)
            session.sid = session_id
        else:
            session_id = session.sid
        
        # 确保session_id是字符串类型
        session_id = self._ensure_string_sid(session_id)
        session.sid = session_id
        
        # 保存session到Redis
        if self.redis is not None:
            try:
                val = self.serializer.dumps(dict(session))
                lifetime = getattr(self, 'permanent_session_lifetime', None) or app.permanent_session_lifetime
                self.redis.setex(
                    self.key_prefix + session_id,
                    lifetime,
                    val
                )
            except Exception as e:
                logger.error(f"保存Session到Redis失败: {str(e)}", exc_info=True)
                return
        
        # 设置cookie
        httponly = getattr(self, 'httponly', True)
        secure = getattr(self, 'secure', app.config.get('SESSION_COOKIE_SECURE', False))
        samesite = getattr(self, 'samesite', app.config.get('SESSION_COOKIE_SAMESITE', 'Lax'))
        
        response.set_cookie(
            app.config["SESSION_COOKIE_NAME"],
            session_id,
            expires=self.get_expiration_time(app, session),
            httponly=httponly,
            domain=domain,
            path=path,
            secure=secure,
            samesite=samesite
        )
    
    def save_session(self, app, session, response):
        """保存 Session 到 Redis 并写入 Cookie。

        用法:
        - 调用方: Flask 请求结束时自动调用
        - 实现: 委托 `_save_session_custom()`，确保 sid 为 str
        """
        # 直接使用自定义实现，避免父类的bytes问题
        self._save_session_custom(app, session, response)
    
    def open_session(self, app, request):
        """从 Cookie 读取 sid 并从 Redis 恢复 Session 数据。

        用法:
        - 调用方: Flask 请求开始时自动调用
        - 签名验证失败: 尝试兼容未签名的旧 Cookie
        - 返回值: Flask Session 对象（空或含 user_id 等数据）
        """
        sid = request.cookies.get(app.config["SESSION_COOKIE_NAME"])
        if not sid:
            return self.session_class()
        
        # 确保sid是字符串类型（从cookie读取的应该是字符串，但为了安全起见）
        sid = self._ensure_string_sid(sid)
        
        # 如果使用签名器，需要验证签名
        if hasattr(self, 'signer') and self.signer is not None:
            try:
                # 尝试unsign，如果失败则返回None
                max_age = getattr(self, 'permanent_session_lifetime', None) or app.permanent_session_lifetime
                unsigned_sid = self.signer.unsign(sid, max_age=max_age)
                if unsigned_sid is None:
                    # 签名验证失败，尝试直接使用原始值（向后兼容未签名的旧Cookie）
                    logger.warning(f"Session签名验证失败，尝试使用原始值: {sid[:50]}")
                    # 不返回空session，继续使用原始sid尝试从Redis读取
                    # 这样可以兼容旧的未签名Cookie
                else:
                    sid = self._ensure_string_sid(unsigned_sid)
            except Exception as e:
                # 签名验证异常，尝试直接使用原始值（向后兼容）
                logger.warning(f"Session签名验证异常: {str(e)}，尝试使用原始值: {sid[:50]}")
                # 不返回空session，继续使用原始sid尝试从Redis读取
        
        # 如果sid为None或空，返回空session
        if not sid:
            return self.session_class()
        
        # 从Redis读取session数据
        if self.redis is None:
            return self.session_class()
        
        try:
            val = self.redis.get(self.key_prefix + sid)
            if val is None:
                logger.warning(f"Redis中未找到Session: {self.key_prefix + sid}")
                return self.session_class()
            data = self.serializer.loads(val)
            return self.session_class(data, sid=sid, permanent=getattr(self, 'permanent', True))
        except Exception as e:
            logger.error(f"从Redis读取Session失败: {str(e)}", exc_info=True)
            return self.session_class()

