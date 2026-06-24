"""PostgreSQL + pgvector 向量存储。

职责总览：
1) 连接与表结构
   - `get_postgres_pool()`  进程级共享连接池（与 Checkpointer 共用）
   - `_ensure_schema()`     建表、索引及 embedding 维度迁移
2) 写入与删除
   - `insert_chunks()`           批量写入文档片段及向量
   - `delete_chunks_for_document()`  按文档删除
   - `delete_chunks_for_kb()`        按知识库删除
3) 检索与读取
   - `vector_search()`       余弦距离 Top-K 向量检索
   - `fetch_chunks_for_kb()` 拉取知识库全部 chunk（供 BM25 内存检索）

数据表 `kb_document_chunks`（PostgreSQL）：
- 元数据在 MySQL（`KbDocument` / `KnowledgeBase`）
- 向量与 chunk 正文存 PG，通过 document_id 关联

相关配置（`Config` / `.env`）：
- `POSTGRES_*`              PostgreSQL 连接
- `KB_EMBEDDING_DIMENSION`  vector 列维度

已知局限与 TODO：
- TODO: `insert_chunks` 改用 COPY / executemany 批量插入，减少逐条 INSERT 往返
- TODO: BM25 全文索引同库（tsvector）或外接 ES，避免 `fetch_chunks_for_kb` 全量拉取
- TODO: 向量索引参数可配置（HNSW m/ef、IVFFlat lists）并按数据量自动选择
- TODO: 软删除 chunk，支持文档版本回溯
- 局限: 进程级共享连接池（与 Checkpointer 共用），多 worker 各自持池（需注意连接总数）
- 局限: 维度迁移时 `USING NULL` 清空已有向量，需触发文档重新入库
- 局限: 远程 PG 空闲断连依赖 `check` + `_run_pg` 重试，极端情况仍可能失败
"""
import json
import logging
from typing import Callable, Dict, List, Optional, TypeVar

from psycopg import OperationalError

from backend.db.postgres_pool import get_postgres_pool, log_pool_stats

logger = logging.getLogger(__name__)

T = TypeVar("T")


class VectorStore:
    """知识库向量与 chunk 的 PostgreSQL 存储层。"""

    _schema_dimension: Optional[int] = None

    def __init__(self, config):
        self.config = config
        self._pool = get_postgres_pool(config)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """建表、 btree 索引、向量索引；维度变更时自动迁移。

        用法:
        - 调用方: `VectorStore.__init__()` 首次实例化时
        - 幂等: 表与索引已存在时跳过创建
        """
        dimension = self.config.KB_EMBEDDING_DIMENSION
        if VectorStore._schema_dimension == dimension:
            return

        statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            f"""
            CREATE TABLE IF NOT EXISTS kb_document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL,
                knowledge_base_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector({dimension}),
                metadata JSONB DEFAULT '{{}}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_kb_chunks_kb_user
                ON kb_document_chunks (knowledge_base_id, user_id)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_kb_chunks_document
                ON kb_document_chunks (document_id)
            """,
        ]

        def _init_schema(conn):
            with conn.cursor() as cur:
                for statement in statements:
                    cur.execute(statement)
                self._sync_embedding_dimension(cur, dimension)
                self._ensure_vector_index(cur)
            conn.commit()

        self._run_pg(_init_schema)
        VectorStore._schema_dimension = dimension

    def _sync_embedding_dimension(self, cur, dimension: int) -> None:
        """当 `KB_EMBEDDING_DIMENSION` 与库中 vector 列不一致时迁移列类型。

        TODO: 迁移后异步任务重新 embedding 全库文档，而非仅清空向量
        """
        cur.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'kb_document_chunks'
            """
        )
        if cur.fetchone() is None:
            return

        current = self._read_embedding_dimension(cur)
        if current is None or current == dimension:
            return

        logger.warning(
            "kb_document_chunks.embedding 维度 %s -> %s，正在迁移",
            current,
            dimension,
        )
        cur.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding_hnsw")
        cur.execute("DROP INDEX IF EXISTS idx_kb_chunks_embedding_ivfflat")
        cur.execute(
            f"""
            ALTER TABLE kb_document_chunks
            ALTER COLUMN embedding TYPE vector({dimension})
            USING NULL
            """
        )

    def _ensure_vector_index(self, cur) -> None:
        """创建 HNSW 向量索引；不支持时降级为 IVFFlat。"""
        cur.execute(
            """
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_kb_chunks_embedding_hnsw'
            """
        )
        if cur.fetchone() is not None:
            return

        try:
            cur.execute(
                """
                CREATE INDEX idx_kb_chunks_embedding_hnsw
                ON kb_document_chunks
                USING hnsw (embedding vector_cosine_ops)
                """
            )
        except Exception:
            cur.execute(
                """
                CREATE INDEX idx_kb_chunks_embedding_ivfflat
                ON kb_document_chunks
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """
            )

    def delete_chunks_for_document(self, document_id: int) -> None:
        """删除指定文档的全部 chunk（文档更新/删除前调用）。"""
        def _delete(conn):
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM kb_document_chunks WHERE document_id = %s",
                    (document_id,),
                )
            conn.commit()

        self._run_pg(_delete)

    def delete_chunks_for_kb(self, knowledge_base_id: int, user_id: int) -> None:
        """删除指定用户某知识库下的全部 chunk。"""
        def _delete(conn):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM kb_document_chunks
                    WHERE knowledge_base_id = %s AND user_id = %s
                    """,
                    (knowledge_base_id, user_id),
                )
            conn.commit()

        self._run_pg(_delete)

    def insert_chunks(
        self,
        *,
        document_id: int,
        knowledge_base_id: int,
        user_id: int,
        chunks: List[str],
        embeddings: List[List[float]],
        filename: str,
    ) -> int:
        """将分块文本与对应向量写入 PostgreSQL。

        用法:
        - 调用方: `KnowledgeService._process_document()`
        - 参数: chunks 与 embeddings 须等长；metadata 记录 filename、chunk_index
        - 返回值: 成功写入的 chunk 数量
        """
        if len(chunks) != len(embeddings):
            raise ValueError("chunks 与 embeddings 数量不一致")

        def _insert(conn):
            with conn.cursor() as cur:
                for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
                    metadata = {
                        "filename": filename,
                        "chunk_index": index,
                    }
                    cur.execute(
                        """
                        INSERT INTO kb_document_chunks
                            (document_id, knowledge_base_id, user_id, chunk_index, content, embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                        """,
                        (
                            document_id,
                            knowledge_base_id,
                            user_id,
                            index,
                            content,
                            self._vector_literal(embedding),
                            json.dumps(metadata, ensure_ascii=False),
                        ),
                    )
            conn.commit()

        self._run_pg(_insert)
        return len(chunks)

    def vector_search(
        self,
        *,
        user_id: int,
        knowledge_base_ids: List[int],
        query_embedding: List[float],
        limit: int,
        enabled_document_ids: Optional[List[int]] = None,
    ) -> List[Dict]:
        """按余弦距离检索与 query 向量最相近的 chunk。

        用法:
        - 调用方: `HybridSearchEngine.search()`
        - 排序: `ORDER BY embedding <=> query`（pgvector 余弦距离）
        - 返回值: 含 vector_score（1 - 距离）的命中列表
        """
        if not knowledge_base_ids:
            return []
        if enabled_document_ids is not None and not enabled_document_ids:
            return []

        def _search(conn):
            with conn.cursor() as cur:
                doc_filter = ""
                params: list = [
                    self._vector_literal(query_embedding),
                    user_id,
                    knowledge_base_ids,
                ]
                if enabled_document_ids is not None:
                    doc_filter = " AND c.document_id = ANY(%s)"
                    params.append(enabled_document_ids)
                params.extend([
                    self._vector_literal(query_embedding),
                    limit,
                ])
                cur.execute(
                    f"""
                    SELECT
                        c.id,
                        c.document_id,
                        c.knowledge_base_id,
                        c.chunk_index,
                        c.content,
                        c.metadata,
                        1 - (c.embedding <=> %s::vector) AS vector_score
                    FROM kb_document_chunks c
                    WHERE c.user_id = %s
                      AND c.knowledge_base_id = ANY(%s)
                      AND c.embedding IS NOT NULL
                      {doc_filter}
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    params,
                )
                return cur.fetchall()

        rows = self._run_pg(_search)
        return [self._row_to_hit(row, source="vector") for row in rows]

    def fetch_chunks_for_document(
        self,
        *,
        user_id: int,
        document_id: int,
    ) -> List[Dict]:
        """拉取指定文档的全部 chunk（按 chunk_index 排序）。"""
        def _fetch(conn):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.id,
                        c.document_id,
                        c.knowledge_base_id,
                        c.chunk_index,
                        c.content,
                        c.metadata
                    FROM kb_document_chunks c
                    WHERE c.user_id = %s AND c.document_id = %s
                    ORDER BY c.chunk_index
                    """,
                    (user_id, document_id),
                )
                return cur.fetchall()

        rows = self._run_pg(_fetch)
        return [self._row_to_hit(row[:6], source="document") for row in rows]

    def update_chunk_content(
        self,
        *,
        chunk_id: int,
        user_id: int,
        document_id: int,
        content: str,
    ) -> bool:
        """更新切片正文并清空向量（需重新 embedding）。"""
        text = (content or "").strip()
        if not text:
            raise ValueError("切片内容不能为空")

        def _update(conn):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE kb_document_chunks
                    SET content = %s, embedding = NULL
                    WHERE id = %s AND user_id = %s AND document_id = %s
                    RETURNING id
                    """,
                    (text, chunk_id, user_id, document_id),
                )
                updated = cur.fetchone() is not None
            conn.commit()
            return updated

        return self._run_pg(_update)

    def update_chunk_embeddings(
        self,
        *,
        user_id: int,
        document_id: int,
        chunk_embeddings: List[tuple],
    ) -> int:
        """批量更新文档切片的 embedding 向量。"""
        if not chunk_embeddings:
            return 0

        def _update(conn):
            count = 0
            with conn.cursor() as cur:
                for chunk_id, embedding in chunk_embeddings:
                    cur.execute(
                        """
                        UPDATE kb_document_chunks
                        SET embedding = %s::vector
                        WHERE id = %s AND user_id = %s AND document_id = %s
                        """,
                        (
                            self._vector_literal(embedding),
                            chunk_id,
                            user_id,
                            document_id,
                        ),
                    )
                    count += cur.rowcount
            conn.commit()
            return count

        return self._run_pg(_update)

    def fetch_chunks_for_kb(
        self,
        *,
        user_id: int,
        knowledge_base_ids: List[int],
        enabled_document_ids: Optional[List[int]] = None,
    ) -> List[Dict]:
        """拉取知识库下全部 chunk 正文（供 BM25 内存检索）。

        用法:
        - 调用方: `HybridSearchEngine.search()` → `Bm25Retriever.search()`
        - 注意: 文档量大时 IO 与内存压力高，见 bm25_retriever TODO
        """
        if enabled_document_ids is not None and not enabled_document_ids:
            return []

        def _fetch(conn):
            with conn.cursor() as cur:
                doc_filter = ""
                params: list = [user_id, knowledge_base_ids]
                if enabled_document_ids is not None:
                    doc_filter = " AND c.document_id = ANY(%s)"
                    params.append(enabled_document_ids)
                cur.execute(
                    f"""
                    SELECT
                        c.id,
                        c.document_id,
                        c.knowledge_base_id,
                        c.chunk_index,
                        c.content,
                        c.metadata
                    FROM kb_document_chunks c
                    WHERE c.user_id = %s
                      AND c.knowledge_base_id = ANY(%s)
                      {doc_filter}
                    ORDER BY c.document_id, c.chunk_index
                    """,
                    params,
                )
                return cur.fetchall()

        rows = self._run_pg(_fetch)
        return [self._row_to_hit(row[:6], source="bm25") for row in rows]

    def _run_pg(self, operation: Callable, retries: int = 2) -> T:
        """执行 PG 操作，连接异常时自动重试。

        用法:
        - 调用方: 本类所有读写方法
        - 重试: 默认最多 3 次（初始 + 2 次重试），应对远程 PG 空闲断连
        """
        last_error: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                with self._pool.connection() as conn:
                    return operation(conn)
            except OperationalError as exc:
                last_error = exc
                log_pool_stats(
                    self._pool,
                    attempt=attempt + 1,
                    max_attempts=retries + 1,
                    error=exc,
                )
        raise last_error

    @staticmethod
    def _read_embedding_dimension(cur) -> Optional[int]:
        """从 pg_catalog 读取 embedding 列的 vector 维度。"""
        cur.execute(
            """
            SELECT atttypmod
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            WHERE c.relname = 'kb_document_chunks' AND a.attname = 'embedding'
            """
        )
        row = cur.fetchone()
        if not row or not row[0] or row[0] <= 0:
            return None
        return int(row[0])

    @staticmethod
    def _vector_literal(values: List[float]) -> str:
        """将浮点列表转为 pgvector 字面量 `[0.1,0.2,...]`。"""
        return "[" + ",".join(f"{v:.8f}" for v in values) + "]"

    @staticmethod
    def _row_to_hit(row, source: str) -> Dict:
        """将 SQL 查询行转为混合检索统一的 hit 字典结构。"""
        metadata = row[5] if len(row) > 5 and row[5] else {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        hit = {
            "id": row[0],
            "document_id": row[1],
            "knowledge_base_id": row[2],
            "chunk_index": row[3],
            "content": row[4],
            "filename": metadata.get("filename"),
            "source": source,
        }
        if len(row) > 6:
            hit["vector_score"] = float(row[6])
        return hit
