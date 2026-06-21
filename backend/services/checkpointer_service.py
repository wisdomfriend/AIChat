"""LangGraph Postgres Checkpointer 单例管理。"""
import logging
import threading

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_checkpointer = None
_pool = None
_lock = threading.Lock()


def init_checkpointer(config) -> PostgresSaver:
    """初始化 Postgres checkpointer 并建表（幂等）。"""
    global _checkpointer, _pool
    with _lock:
        if _checkpointer is not None:
            return _checkpointer

        conn_string = config.POSTGRES_URI
        # setup 含 CREATE INDEX CONCURRENTLY，必须在 autocommit 连接上执行
        with PostgresSaver.from_conn_string(conn_string) as setup_saver:
            setup_saver.setup()
        _pool = ConnectionPool(
            conninfo=conn_string,
            max_size=10,
            open=True,
            check=ConnectionPool.check_connection,
            max_idle=300,
            reconnect_timeout=300,
            kwargs={"connect_timeout": 10},
        )
        _checkpointer = PostgresSaver(_pool)
        logger.info("Postgres checkpointer 已初始化: %s", config.POSTGRES_HOST)
        return _checkpointer


def get_checkpointer() -> PostgresSaver:
    """获取全局 checkpointer；未初始化时按 Config 自动初始化。"""
    if _checkpointer is None:
        from ..config import Config

        return init_checkpointer(Config())
    return _checkpointer


def delete_thread(session_id: int) -> None:
    """删除会话对应的 Agent checkpoint thread。"""
    try:
        checkpointer = get_checkpointer()
        checkpointer.delete_thread(str(session_id))
    except Exception as e:
        logger.warning("删除 checkpoint thread 失败 session=%s: %s", session_id, e)
