"""PostgreSQL 进程级连接池（VectorStore / Checkpointer 共用单例）。

连接数规划（生产 gunicorn 默认 4 worker）：
  进程总连接峰值 ≈ workers × POSTGRES_POOL_MAX_SIZE
  建议 workers × max_size + 预留(10~20) < PostgreSQL max_connections（默认 100）

查看 PG 上限：
  psql -c "SHOW max_connections;"
  psql -c "SELECT count(*) FROM pg_stat_activity;"
"""
import logging
import threading
from typing import Optional

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_pool: Optional[ConnectionPool] = None
_lock = threading.Lock()


def get_postgres_pool(config) -> ConnectionPool:
    """获取进程级 PostgreSQL 连接池单例。"""
    global _pool
    if _pool is not None:
        return _pool

    with _lock:
        if _pool is not None:
            return _pool

        min_size = config.POSTGRES_POOL_MIN_SIZE
        max_size = config.POSTGRES_POOL_MAX_SIZE
        if min_size > max_size:
            raise ValueError(
                f"POSTGRES_POOL_MIN_SIZE({min_size}) 不能大于 POSTGRES_POOL_MAX_SIZE({max_size})"
            )

        _pool = ConnectionPool(
            conninfo=config.POSTGRES_URI,
            min_size=min_size,  # 池至少保持 x 条连接
            max_size=max_size,  # 池最多保持 x 条连接
            timeout=config.POSTGRES_POOL_TIMEOUT,  # 从池里借连接时，若 x 条都在用，最多排队等 x 秒
            open=True,  # 创建池时立即打开（预热）
            check=ConnectionPool.check_connection,  # 从池里取连接前做健康检查（SELECT 1），断连的会被丢弃并重连
            max_idle=300,  # 空闲连接超过 300 秒会被关闭
            reconnect_timeout=300,  # 断连后重连最多等 300 秒
            kwargs={"connect_timeout": 10},  # 新建 TCP 连接时，连不上 PG 最多等 10 秒
        )
        logger.info(
            "PostgreSQL 连接池已创建: min_size=%s max_size=%s timeout=%ss host=%s",
            min_size,
            max_size,
            config.POSTGRES_POOL_TIMEOUT,
            config.POSTGRES_HOST,
        )
        _log_pg_connection_limits(_pool, min_size, max_size)
        return _pool


def log_pool_stats(
        pool: ConnectionPool,
        *,
        attempt: int,
        max_attempts: int,
        error: Exception,
) -> None:
    """连接异常时输出池状态，便于排查池满或断连。"""
    stats = {}
    try:
        stats = pool.get_stats()
    except Exception as exc:
        logger.debug("无法读取连接池 stats: %s", exc)

    logger.warning(
        "PostgreSQL 连接异常 (attempt %s/%s): %s | pool_stats=%s",
        attempt,
        max_attempts,
        error,
        _format_pool_stats(stats),
    )


def _format_pool_stats(stats) -> dict:
    if not stats:
        return {}
    keys = (
        "pool_min",
        "pool_max",
        "pool_size",
        "pool_available",
        "requests_waiting",
        "connections_num",
        "connections_ms",
    )
    if isinstance(stats, dict):
        return {k: stats.get(k) for k in keys if k in stats}
    return {k: getattr(stats, k, None) for k in keys if hasattr(stats, k)}


def _log_pg_connection_limits(
        pool: ConnectionPool,
        min_size: int,
        max_size: int,
) -> None:
    """启动时查询 PG max_connections 与当前活跃连接数。"""
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SHOW max_connections")
                max_connections = int(cur.fetchone()[0])
                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """
                )
                active = cur.fetchone()[0]
        logger.info(
            "PostgreSQL max_connections=%s，当前库活跃连接=%s；"
            "本进程池 min_size=%s max_size=%s",
            max_connections,
            active,
            min_size,
            max_size,
        )
    except Exception as exc:
        logger.warning("无法查询 PostgreSQL max_connections: %s", exc)
