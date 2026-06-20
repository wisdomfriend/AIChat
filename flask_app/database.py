"""数据库连接与会话管理。

职责总览：
1) 连接池
   - `create_engine_instance()`  创建带连接池的 SQLAlchemy Engine
   - `init_db()`  初始化全局 Engine（失败时最多重试 5 次）
2) 会话获取
   - `get_session()`  直接返回 ORM Session（路由/Service 层常用）
   - `get_db()`  生成器式 Session，适用于依赖注入场景
"""
import logging
import time

from flask import current_app
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.orm import sessionmaker

from .models import Base

logger = logging.getLogger(__name__)


def get_database_url():
    """读取当前配置的数据库连接 URL。

    用法:
    - 调用方: `create_engine_instance()`
    - 返回值: `Config().DATABASE_URL`
    """
    from .config import Config
    config = Config()
    return config.DATABASE_URL


def create_engine_instance():
    """创建带连接池与 pre-ping 的数据库 Engine。

    用法:
    - 调用方: `init_db()`
    - 连接池: pool_size=10, max_overflow=20, pool_recycle=3600
    - 返回值: SQLAlchemy Engine 实例
    """
    database_url = get_database_url()

    engine = create_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            'connect_timeout': 10,
            'charset': 'utf8mb4'
        }
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """连接建立时的调试回调（内部使用）。"""
        logger.debug("数据库连接已建立")

    return engine


def create_session_local(engine):
    """创建绑定 Engine 的 Session 工厂（内部使用）。"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


_engine = None
_SessionLocal = None


def init_db():
    """初始化全局 Engine 与 Session 工厂，带重试机制。

    用法:
    - 调用方: `flask_app.create_app()`
    - 重试: 最多 5 次，间隔 3 秒
    - 返回值: `(engine, SessionLocal)` 元组
    - 失败: 抛出 OperationalError
    """
    global _engine, _SessionLocal
    if _engine is None:
        max_retries = 5
        retry_delay = 3

        for attempt in range(max_retries):
            try:
                _engine = create_engine_instance()
                with _engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                _SessionLocal = create_session_local(_engine)
                ensure_schema()
                return _engine, _SessionLocal
            except (OperationalError, DisconnectionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"数据库连接失败，已重试 {max_retries} 次: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"数据库初始化错误: {str(e)}", exc_info=True)
                raise

    return _engine, _SessionLocal


_schema_ready = False


def ensure_schema():
    """补齐运行时所需的数据库字段（幂等）。"""
    global _engine, _schema_ready
    if _schema_ready:
        return
    if _engine is None:
        init_db()

    migrations = [
        (
            "chat_sessions",
            "is_pinned",
            "ALTER TABLE chat_sessions ADD COLUMN is_pinned BOOLEAN DEFAULT FALSE COMMENT '是否固定到侧栏顶部'",
        ),
    ]

    with _engine.begin() as conn:
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


def get_db():
    """生成器式获取数据库 Session（依赖注入场景）。

    用法:
    - 调用方: 需要 `yield` 模式的框架集成
    - 返回值: 生成器，yield 一个 Session，结束后自动 close
    """
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """直接获取数据库 Session（路由/Service 层常用）。

    用法:
    - 调用方: 各 Service、`utils.get_current_user()` 等
    - 返回值: SQLAlchemy Session 实例
    - 注意: 调用方负责 `db.close()` 或使用 try/finally
    """
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
