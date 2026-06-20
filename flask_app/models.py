"""SQLAlchemy ORM 模型定义。

表总览（按业务领域）：
1) 用户与认证
   - `User`    账号、密码哈希、admin 标志
   - `ApiKey`  LLM 提供商 API 密钥
2) 聊天
   - `ChatSession`          会话主题与 LLM 提供商
   - `ChatMessage`          用户/助手消息及附件 ID
   - `ConversationSummary`  长对话压缩摘要
3) 文件与统计
   - `UploadedFile`  上传文件元数据与提取文本
   - `TokenUsage`    Token 用量记录
"""
from sqlalchemy import Boolean, Column, Integer, String, Text, TIMESTAMP, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """用户表 `users`，存储登录凭证与权限标志。"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    last_login = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)


class ApiKey(Base):
    """API 密钥表 `api_keys`，按 LLM 提供商存储密钥。"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    api_key = Column(String(255), nullable=False)
    provider = Column(String(50), default='deepseek')
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))


class TokenUsage(Base):
    """Token 用量表 `token_usage`，记录每次 LLM 调用的消耗。"""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    model = Column(String(50), default='deepseek-chat')
    request_time = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class ChatSession(Base):
    """聊天会话表 `chat_sessions`，每个用户可有多个会话。"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    llm_provider = Column(String(50), default='deepseek')
    is_pinned = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))


class ChatMessage(Base):
    """聊天消息表 `chat_messages`，关联会话与用户/助手角色。"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    file_ids = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class UploadedFile(Base):
    """上传文件表 `uploaded_files`，存储文件元数据与提取文本。"""
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_type = Column(String(100), nullable=False)
    file_extension = Column(String(20), nullable=False)
    extracted_text = Column(String(16777215))
    text_length = Column(Integer, default=0)
    extraction_status = Column(String(20), default='pending')
    error_message = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'), onupdate=text('CURRENT_TIMESTAMP'))


class ConversationSummary(Base):
    """对话摘要表 `conversation_summaries`，存储上下文压缩结果。"""
    __tablename__ = "conversation_summaries"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, nullable=False)
    message_count = Column(Integer, nullable=False)
    summary_content = Column(Text, nullable=False)
    token_count = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
