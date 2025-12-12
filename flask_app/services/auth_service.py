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
            print(f"Authentication error: {e}")
            return {
                'success': False,
                'message': '数据库连接错误，请稍后重试！'
            }
        finally:
            db.close()

