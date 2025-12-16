"""认证服务"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
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
            
            if not user or not user.is_active:
                return {
                    'success': False,
                    'message': '用户名或密码错误！'
                }
            
            # 检查密码（支持加密密码和明文密码兼容）
            password_valid = False
            
            # 判断是否是werkzeug生成的哈希格式（pbkdf2, scrypt, argon2等）
            # werkzeug哈希格式通常以算法名开头，包含冒号分隔符
            is_werkzeug_hash = ':' in user.password and (
                user.password.startswith('pbkdf2:') or 
                user.password.startswith('scrypt:') or
                user.password.startswith('argon2:')
            )
            
            if is_werkzeug_hash:
                # 使用check_password_hash验证（支持所有werkzeug生成的哈希格式）
                # check_password_hash会自动识别哈希算法（pbkdf2:sha256, scrypt等）
                password_valid = check_password_hash(user.password, password)
            else:
                # 明文密码（兼容旧用户）
                password_valid = (user.password == password)
            
            if password_valid:
                # 如果密码是明文，升级为加密密码
                if not is_werkzeug_hash:
                    user.password = generate_password_hash(password)
                    db.commit()
                
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
    
    @staticmethod
    def _generate_invite_code():
        """
        生成邀请码：取当前日期的"日"部分的最后一位，重复4次
        
        Returns:
            str: 4位数字的邀请码
        """
        today = datetime.now()
        day = today.day
        last_digit = str(day)[-1]  # 取日的最后一位数字
        invite_code = last_digit * 4  # 重复4次
        return invite_code
    
    @staticmethod
    def register(username, password, password_confirm=None, invite_code=None):
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            password_confirm: 确认密码（可选，如果提供则验证一致性）
            invite_code: 邀请码（必填）
        
        Returns:
            dict: 包含success和message的字典
        """
        db = get_session()
        try:
            # 0. 验证邀请码
            if not invite_code or len(invite_code.strip()) == 0:
                return {
                    'success': False,
                    'message': '邀请码不能为空！'
                }
            
            invite_code = invite_code.strip()
            
            # 生成正确的邀请码
            correct_invite_code = AuthService._generate_invite_code()
            
            if invite_code != correct_invite_code:
                return {
                    'success': False,
                    'message': '邀请码错误，请检查后重试！'
                }
            
            # 1. 验证用户名
            if not username or len(username.strip()) == 0:
                return {
                    'success': False,
                    'message': '用户名不能为空！'
                }
            
            username = username.strip()
            
            # 用户名长度验证（3-20个字符）
            if len(username) < 3:
                return {
                    'success': False,
                    'message': '用户名至少需要3个字符！'
                }
            
            if len(username) > 20:
                return {
                    'success': False,
                    'message': '用户名不能超过20个字符！'
                }
            
            # 用户名格式验证（只允许字母、数字、下划线）
            if not username.replace('_', '').isalnum():
                return {
                    'success': False,
                    'message': '用户名只能包含字母、数字和下划线！'
                }
            
            # 2. 验证密码
            if not password or len(password) == 0:
                return {
                    'success': False,
                    'message': '密码不能为空！'
                }
            
            # 密码长度验证（至少6个字符）
            if len(password) < 6:
                return {
                    'success': False,
                    'message': '密码至少需要6个字符！'
                }
            
            if len(password) > 128:
                return {
                    'success': False,
                    'message': '密码不能超过128个字符！'
                }
            
            # 3. 验证确认密码（如果提供）
            if password_confirm is not None:
                if password != password_confirm:
                    return {
                        'success': False,
                        'message': '两次输入的密码不一致！'
                    }
            
            # 4. 检查用户名是否已存在
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                return {
                    'success': False,
                    'message': '该用户名已被注册，请选择其他用户名！'
                }
            
            # 5. 创建新用户
            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                password=hashed_password,
                is_active=True
            )
            
            db.add(new_user)
            db.commit()
            
            return {
                'success': True,
                'message': '注册成功！',
                'user': {
                    'id': new_user.id,
                    'username': new_user.username
                }
            }
            
        except Exception as e:
            db.rollback()
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"注册用户时出错: {str(e)}", exc_info=True)
            
            # 处理数据库唯一性约束错误
            error_str = str(e).lower()
            if 'unique' in error_str or 'duplicate' in error_str:
                return {
                    'success': False,
                    'message': '该用户名已被注册，请选择其他用户名！'
                }
            
            return {
                'success': False,
                'message': f'注册失败：{str(e)}'
            }
        finally:
            db.close()

