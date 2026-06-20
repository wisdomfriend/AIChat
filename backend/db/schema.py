"""数据库 schema 迁移与字段补齐（幂等）。"""
import logging

from sqlalchemy import text

from backend.db.connection import init_db

logger = logging.getLogger(__name__)

_schema_ready = False


def ensure_schema():
    """补齐运行时所需的数据库字段（幂等）。"""
    global _schema_ready
    if _schema_ready:
        return

    engine, _ = init_db()

    migrations = [
        (
            "chat_sessions",
            "is_pinned",
            "ALTER TABLE chat_sessions ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE COMMENT '是否固定到侧栏顶部'",
        ),
        (
            "chat_messages",
            "metadata",
            "ALTER TABLE chat_messages ADD COLUMN metadata TEXT NULL COMMENT 'JSON: tool_calls 等扩展信息'",
        ),
    ]

    with engine.begin() as conn:
        for table, column, ddl in migrations:
            exists = conn.execute(
                text(
                    """
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = :table
                      AND COLUMN_NAME = :column
                    """
                ),
                {"table": table, "column": column},
            ).scalar()
            if not exists:
                conn.execute(text(ddl))
                logger.info("已添加数据库字段: %s.%s", table, column)

        index_exists = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'chat_sessions'
                  AND INDEX_NAME = 'idx_chat_sessions_pinned'
                """
            )
        ).scalar()
        if not index_exists:
            conn.execute(
                text(
                    "CREATE INDEX idx_chat_sessions_pinned ON chat_sessions (user_id, is_pinned, updated_at)"
                )
            )
            logger.info("已添加索引: idx_chat_sessions_pinned")

    _schema_ready = True
