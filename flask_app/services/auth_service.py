"""认证服务"""
from datetime import datetime
from ..database import get_session
from ..models import User


class AuthService:
    """认证相关业务逻辑"""
    
    @staticmethod
    def authenticate(username, password):
        """验证用户登录"""
        db = get_session()
        try:
            user = db.query(User).filter(User.username == username).first()
            
            if user and user.password == password and user.is_active:
                # 更新最后登录时间
                user.last_login = datetime.utcnow()
                db.commit()
                return {
                    'success': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'last_login': user.last_login
                    }
                }
            else:
                return {
                    'success': False,
                    'message': '用户名或密码错误！'
                }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"数据库连接错误: {str(e)}", exc_info=True)
            # 提供更详细的错误信息（仅用于调试，生产环境可以隐藏）
            error_msg = '数据库连接错误，请稍后重试！'
            # 如果是常见的连接错误，提供更具体的提示
            error_str = str(e).lower()
            if 'unknown host' in error_str or 'name or service not known' in error_str:
                error_msg = '数据库连接错误：无法解析数据库主机地址，请检查 MYSQL_HOST 配置！'
            elif 'access denied' in error_str or 'authentication failed' in error_str:
                error_msg = '数据库连接错误：认证失败，请检查数据库用户名和密码！'
            elif 'unknown database' in error_str:
                error_msg = '数据库连接错误：数据库不存在，请检查 MYSQL_DB 配置！'
            elif 'connection refused' in error_str or 'can\'t connect' in error_str:
                error_msg = '数据库连接错误：无法连接到数据库服务器，请检查数据库服务是否运行！'
            return {
                'success': False,
                'message': error_msg
            }
        finally:
            db.close()

