"""数据库连接和会话管理"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import current_app
from .models import Base


def get_database_url():
    """获取数据库连接URL"""
    from .config import Config
    config = Config()
    return config.DATABASE_URL


def create_engine_instance():
    """创建数据库引擎"""
    return create_engine(get_database_url(), echo=False)


def create_session_local(engine):
    """创建会话工厂"""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 全局引擎和会话工厂
_engine = None
_SessionLocal = None


def init_db():
    """初始化数据库连接"""
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_engine_instance()
        _SessionLocal = create_session_local(_engine)
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

