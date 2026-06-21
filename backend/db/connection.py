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

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None


def _get_database_url() -> str:
    """读取当前配置的数据库连接 URL。"""
    try:
        from backend.config import get_config

        return get_config().DATABASE_URL
    except RuntimeError:
        from backend.config import Config

        return Config().DATABASE_URL


def create_engine_instance():
    """创建带连接池与 pre-ping 的数据库 Engine。"""
    database_url = _get_database_url()

    engine = create_engine(
        database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 10,
            "charset": "utf8mb4",
        },
    )

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, connection_record):
        logger.debug("数据库连接已建立")

    return engine


def create_session_local(engine):
    """创建绑定 Engine 的 Session 工厂。"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_tables(engine):
    """根据 ORM 模型创建缺失的数据库表（幂等）。

    仅在当前进程首次 init_db() 时调用一次（见 _engine 守卫），
    不会在每次 HTTP 请求时重复执行。create_all(checkfirst=True) 会先
    检查表是否已存在，已有表时几乎无额外开销。
    """
    import backend.db.models  # noqa: F401 — 注册全部模型到 Base.metadata

    from backend.db.models import Base

    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("数据库表结构已就绪")


def init_db():
    """初始化全局 Engine 与 Session 工厂，带重试机制。"""
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
                _create_tables(_engine)
                return _engine, _SessionLocal
            except (OperationalError, DisconnectionError) as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        "数据库连接失败 (尝试 %s/%s): %s",
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    logger.info("等待 %s 秒后重试...", retry_delay)
                    time.sleep(retry_delay)
                else:
                    logger.error("数据库连接失败，已重试 %s 次: %s", max_retries, e)
                    raise
            except Exception as e:
                logger.error("数据库初始化错误: %s", e, exc_info=True)
                raise

    return _engine, _SessionLocal


def get_db():
    """生成器式获取数据库 Session（依赖注入场景）。"""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """直接获取数据库 Session（路由/Service 层常用）。"""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()
