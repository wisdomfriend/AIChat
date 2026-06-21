"""混合检索 — 向量 + BM25 + RRF 融合 + Rerank。

职责总览：
1) 多路召回
   - 向量检索（`VectorStore.vector_search`）  语义相似 Top-N
   - 关键词检索（`Bm25Retriever.search`）     字面匹配 Top-N
2) 结果融合
   - `_reciprocal_rank_fusion()`  RRF 倒数排名融合，合并两路候选
3) 精排与输出
   - `RerankClient.rerank()`  对融合后的候选重排序（可选，依赖外部 API）
   - `format_results_for_agent()`  格式化为 Agent 可读的引用文本

检索流水线（单次 `search()`）：
  query
    ├─→ embed_query → vector_search     → vector_candidates
    └─→ fetch_chunks_for_kb → BM25       → bm25_candidates
              ↓
         RRF 融合 → rerank_pool → Rerank API → 最终结果

相关配置（`Config` / `.env`）：
- `KB_TOP_K`              最终返回条数
- `KB_VECTOR_CANDIDATES`  向量召回数量
- `KB_BM25_CANDIDATES`    BM25 召回数量
- `KB_RERANK_CANDIDATES`  送入 Rerank 的候选数量
- `KB_RRF_K`              RRF 平滑常数（默认 60）

已知局限与 TODO：
- TODO: 向量检索与 BM25 检索并行执行（asyncio / 线程池），降低端到端延迟
- TODO: BM25 索引落库后，`fetch_chunks_for_kb` 全量拉取可改为按 kb_id 索引查询
- TODO: 支持可配置的融合策略（加权 RRF、向量/BM25 分数归一化后再融合）
- TODO: 同一 session 内对相同 query 缓存 embedding，避免重复调用 Embedding API
- TODO: Rerank 不可用时提供更明确的降级策略（如按 fusion_score 截断并标注来源）
- 局限: 每次检索至少 1 次 Embedding API + 1 次全量 chunk 读取（供 BM25）
- 局限: Rerank 依赖外部 API；未配置时直接返回 RRF 融合结果（`source: hybrid`）
- 局限: 多知识库检索时未按库内相关性做二次加权
"""
from typing import Dict, List, Optional

from .bm25_retriever import Bm25Retriever
from .embedding_client import EmbeddingClient
from .rerank_client import RerankClient
from .vector_store import VectorStore


class HybridSearchEngine:
    """知识库混合检索引擎。

    组合向量存储、Embedding、BM25、Rerank 客户端，对外提供统一的 `search()` 入口。
    由 `KnowledgeService` 在 API 检索与 Agent `knowledge_search` 工具中调用。
    """

    def __init__(self, config):
        self.config = config
        self.vector_store = VectorStore(config)
        self.embedding_client = EmbeddingClient(config)
        self.rerank_client = RerankClient(config)
        self.bm25_retriever = Bm25Retriever()

    def search(
        self,
        user_id: int,
        knowledge_base_ids: List[int],
        query: str,
        top_k: Optional[int] = None,
    ) -> List[Dict]:
        """执行混合检索，返回与 query 最相关的文档片段列表。

        用法:
        - 调用方: `KnowledgeService.search()` / `search_for_agent()`
        - 参数:
            - user_id: 当前用户 ID（向量与 chunk 查询均按用户隔离）
            - knowledge_base_ids: 待检索的知识库 ID 列表
            - query: 检索问题
            - top_k: 最终返回条数，默认 `KB_TOP_K`
        - 返回值: 命中片段列表，每项含 content、filename、document_id、
                  chunk_index 及 fusion_score / rerank_score（如有）

        流程:
        1. 向量召回 `KB_VECTOR_CANDIDATES` 条
        2. 拉取知识库全部 chunk，BM25 召回 `KB_BM25_CANDIDATES` 条
        3. RRF 融合两路结果
        4. 取前 `KB_RERANK_CANDIDATES` 条送 Rerank；成功则返回 `source: hybrid+rerank`
        5. Rerank 未启用或失败时，返回融合结果前 top_k 条（`source: hybrid`）
        """
        if not knowledge_base_ids:
            return []

        top_k = top_k or self.config.KB_TOP_K
        vector_candidates = self.vector_store.vector_search(
            user_id=user_id,
            knowledge_base_ids=knowledge_base_ids,
            query_embedding=self.embedding_client.embed_query(query),
            limit=self.config.KB_VECTOR_CANDIDATES,
        )
        all_chunks = self.vector_store.fetch_chunks_for_kb(
            user_id=user_id,
            knowledge_base_ids=knowledge_base_ids,
        )
        bm25_candidates = self.bm25_retriever.search(
            query=query,
            chunks=all_chunks,
            top_k=self.config.KB_BM25_CANDIDATES,
        )

        fused = self._reciprocal_rank_fusion(vector_candidates, bm25_candidates)
        if not fused:
            return []

        rerank_pool = fused[: self.config.KB_RERANK_CANDIDATES]
        documents = [item["content"] for item in rerank_pool]
        rerank_results = self.rerank_client.rerank(
            query=query,
            documents=documents,
            top_n=top_k,
        )

        if self.rerank_client.enabled and rerank_results:
            final = []
            for result in rerank_results:
                idx = result["index"]
                if 0 <= idx < len(rerank_pool):
                    item = dict(rerank_pool[idx])
                    item["rerank_score"] = result["relevance_score"]
                    item["source"] = "hybrid+rerank"
                    final.append(item)
            return final

        for item in rerank_pool[:top_k]:
            item["source"] = "hybrid"
        return rerank_pool[:top_k]

    def _reciprocal_rank_fusion(
        self,
        vector_hits: List[Dict],
        bm25_hits: List[Dict],
    ) -> List[Dict]:
        """RRF（Reciprocal Rank Fusion）融合向量与 BM25 两路召回结果。

        公式: fusion_score(chunk) += 1 / (KB_RRF_K + rank + 1)
        同一片段在两路均出现时分数累加，排名越靠前贡献越大。

        用法:
        - 调用方: `search()` 内部
        - 参数: 两路已按各自分数降序排列的命中列表（需含 `id` 字段）
        - 返回值: 按 fusion_score 降序的去重片段列表

        TODO:
        - 支持按路加权（如向量 0.6 + BM25 0.4）
        - 融合前保留 vector_score / bm25_score 便于调试与可解释性
        """
        scores: Dict[int, float] = {}
        payload: Dict[int, Dict] = {}
        rrf_k = self.config.KB_RRF_K

        for rank, item in enumerate(vector_hits):
            chunk_id = item["id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            payload[chunk_id] = item

        for rank, item in enumerate(bm25_hits):
            chunk_id = item["id"]
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank + 1)
            payload.setdefault(chunk_id, item)

        ordered_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
        results = []
        for chunk_id in ordered_ids:
            item = dict(payload[chunk_id])
            item["fusion_score"] = scores[chunk_id]
            results.append(item)
        return results

    @staticmethod
    def format_results_for_agent(results: List[Dict]) -> str:
        """将检索结果格式化为 Agent 工具返回的引用文本。

        用法:
        - 调用方: `KnowledgeService.search_for_agent()` / Agent `knowledge_search` 工具链
        - 参数: `search()` 返回的命中列表
        - 返回值: 带来源标注的多段文本；无结果时返回固定提示语

        输出格式示例:
            [来源 1] 文档: 产品手册.md | 片段 #3
            Nova X1 Ultra 起售价 ¥6,999 ...
        """
        if not results:
            return "知识库中未找到相关内容。"

        parts = []
        for idx, item in enumerate(results, start=1):
            filename = item.get("filename") or "未知文档"
            chunk_index = item.get("chunk_index", 0)
            content = item.get("content", "")
            parts.append(
                f"[来源 {idx}] 文档: {filename} | 片段 #{chunk_index + 1}\n{content}"
            )
        return "\n\n---\n\n".join(parts)
