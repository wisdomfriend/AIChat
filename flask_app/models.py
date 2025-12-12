"""数据库模型定义"""
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    last_login = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)


class ApiKey(Base):
    """API密钥配置模型"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), nullable=False)
    provider = Column(String(50), default='deepseek')
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))


class TokenUsage(Base):
    """Token使用记录模型"""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    model = Column(String(50), default='deepseek-chat')
    request_time = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

