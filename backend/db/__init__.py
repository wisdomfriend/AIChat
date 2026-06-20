"""数据库层统一导出。

模块总览：
1) connection  — SQLAlchemy Engine / Session 连接管理
2) schema      — 运行时 schema 迁移与字段补齐
3) models      — ORM 模型定义
"""
from backend.db.connection import get_db, get_session, init_db
from backend.db.models import (
    ApiKey,
    Base,
    ChatMessage,
    ChatSession,
    ConversationSummary,
    TokenUsage,
    UploadedFile,
    User,
)
from backend.db.schema import ensure_schema

__all__ = [
    "ApiKey",
    "Base",
    "ChatMessage",
    "ChatSession",
    "ConversationSummary",
    "TokenUsage",
    "UploadedFile",
    "User",
    "ensure_schema",
    "get_db",
    "get_session",
    "init_db",
]
