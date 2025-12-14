"""数据库连接和会话管理"""
import time
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError
from flask import current_app
from .models import Base

logger = logging.getLogger(__name__)


def get_database_url():
    """获取数据库连接URL"""
    from .config import Config
    config = Config()
    return config.DATABASE_URL


def create_engine_instance():
    """创建数据库引擎，带连接池和重试机制"""
    database_url = get_database_url()
    
    # 配置连接池参数
    engine = create_engine(
        database_url,
        echo=False,
        pool_size=10,  # 连接池大小
        max_overflow=20,  # 最大溢出连接数
        pool_pre_ping=True,  # 连接前ping，自动重连断开的连接
        pool_recycle=3600,  # 连接回收时间（秒）
        connect_args={
            'connect_timeout': 10,  # 连接超时时间（秒）
            'charset': 'utf8mb4'
        }
    )
    
    # 添加连接错误处理
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """连接建立时的回调"""
        logger.debug("数据库连接已建立")
    
    return engine


def create_session_local(engine):
    """创建会话工厂"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 全局引擎和会话工厂
_engine = None
_SessionLocal = None


def init_db():
    """初始化数据库连接，带重试机制"""
    global _engine, _SessionLocal
    if _engine is None:
        max_retries = 5
        retry_delay = 3  # 秒
        
        for attempt in range(max_retries):
            try:
                _engine = create_engine_instance()
                # 测试连接
                with _engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                _SessionLocal = create_session_local(_engine)
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


def get_db():
    """获取数据库会话（用于依赖注入）"""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """获取数据库会话（直接使用）"""
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()

