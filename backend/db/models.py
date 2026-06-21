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
4) 知识库
   - `KnowledgeBase`  用户知识库
   - `KbDocument`     知识库文档元数据
"""
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """用户表 `users`，存储登录凭证与权限标志。"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    last_login = Column(TIMESTAMP, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)


class ApiKey(Base):
    """API 密钥表 `api_keys`，按 LLM 提供商存储密钥。"""
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    api_key = Column(String(255), nullable=False)
    provider = Column(String(50), default="deepseek")
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class TokenUsage(Base):
    """Token 用量表 `token_usage`，记录每次 LLM 调用的消耗。"""
    __tablename__ = "token_usage"
    __table_args__ = (
        Index("idx_token_usage_user_id", "user_id"),
        Index("idx_token_usage_request_time", "request_time"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    model = Column(String(50), default="deepseek-chat")
    request_time = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class ChatSession(Base):
    """聊天会话表 `chat_sessions`，每个用户可有多个会话。"""
    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("idx_chat_sessions_user_id", "user_id"),
        Index("idx_chat_sessions_updated_at", "updated_at"),
        Index("idx_chat_sessions_pinned", "user_id", "is_pinned", "updated_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    llm_provider = Column(String(50), default="deepseek")
    is_pinned = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class ChatMessage(Base):
    """聊天消息表 `chat_messages`，关联会话与用户/助手角色。"""
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("idx_chat_messages_session_id", "session_id"),
        Index("idx_chat_messages_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    file_ids = Column(String(500))
    metadata_json = Column("metadata", Text)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))


class UploadedFile(Base):
    """上传文件表 `uploaded_files`，存储文件元数据与提取文本。"""
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("idx_uploaded_files_user_id", "user_id"),
        Index("idx_uploaded_files_stored_filename", "stored_filename"),
        Index("idx_uploaded_files_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_type = Column(String(100), nullable=False)
    file_extension = Column(String(20), nullable=False)
    extracted_text = Column(Text)
    text_length = Column(Integer, default=0)
    extraction_status = Column(String(20), default="pending")
    error_message = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class KnowledgeBase(Base):
    """知识库表 `knowledge_bases`，每个用户可创建多个知识库。"""
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("idx_knowledge_bases_user_id", "user_id"),
        Index("idx_knowledge_bases_updated_at", "updated_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    document_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class KbDocument(Base):
    """知识库文档表 `kb_documents`，存储文档元数据与处理状态。"""
    __tablename__ = "kb_documents"
    __table_args__ = (
        Index("idx_kb_documents_kb_id", "knowledge_base_id"),
        Index("idx_kb_documents_user_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    knowledge_base_id = Column(
        Integer, ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_extension = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    chunk_count = Column(Integer, default=0)
    error_message = Column(String(500))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(
        TIMESTAMP,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
    )


class ConversationSummary(Base):
    """对话摘要表 `conversation_summaries`，存储上下文压缩结果。"""
    __tablename__ = "conversation_summaries"
    __table_args__ = (Index("idx_session_created", "session_id", "created_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    message_count = Column(Integer, nullable=False)
    summary_content = Column(Text, nullable=False)
    token_count = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
