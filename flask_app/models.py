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
    is_admin = Column(Boolean, default=False)


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


class ChatSession(Base):
    """聊天会话模型"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)  # 会话主题
    llm_provider = Column(String(50), default='deepseek')  # 使用的LLM提供商
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))


class ChatMessage(Base):
    """聊天消息模型"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)  # 关联的会话ID
    role = Column(String(20), nullable=False)  # 'user' 或 'assistant'
    content = Column(String(10000), nullable=False)  # 消息内容
    file_ids = Column(String(500))  # 关联的文件ID列表，JSON格式 如 "[1,2,3]"
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class UploadedFile(Base):
    """上传文件模型"""
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)                    # 用户ID
    original_filename = Column(String(255), nullable=False)      # 原始文件名
    stored_filename = Column(String(255), nullable=False)        # 存储的文件名(UUID)
    file_path = Column(String(500), nullable=False)              # 文件存储路径
    file_size = Column(Integer, nullable=False)                  # 文件大小(字节)
    file_type = Column(String(100), nullable=False)              # 文件MIME类型
    file_extension = Column(String(20), nullable=False)          # 文件扩展名
    extracted_text = Column(String(16777215))                    # 提取的文本内容 (MEDIUMTEXT)
    text_length = Column(Integer, default=0)                     # 提取文本的长度
    extraction_status = Column(String(20), default='pending')    # pending/success/failed/too_large
    error_message = Column(String(500))                          # 错误信息
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))