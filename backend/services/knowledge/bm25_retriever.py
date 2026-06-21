"""BM25 关键词检索 — 基于 rank_bm25。

职责总览：
1) 分词
   - `tokenize()`  将中英文文本拆为 token 列表（供 BM25 统计词频）
2) 检索
   - `Bm25Retriever.search()`  对内存中的 chunk 列表打分并返回 Top-K

在混合检索中的位置（见 `hybrid_search.py`）：
- 向量检索负责语义相似；BM25 负责型号、专有名词等字面匹配
- 两路结果经 RRF 融合后交给 Rerank 精排

已知局限与 TODO：
- TODO: 中文分词改用 jieba（或 pkuseg），避免单字切分导致「知识库」等词无法整词匹配
- TODO: BM25 索引持久化到数据库（如 PostgreSQL tsvector、Elasticsearch、Meilisearch），
        避免每次检索从 PG 拉全量 chunk 并在内存重建索引
- TODO: 按 knowledge_base_id 维护独立索引，支持增量更新（文档上传/删除时更新索引）
- TODO: 大规模语料时考虑分片检索或缓存 BM25Okapi 实例（注意多进程/多请求隔离）
- 局限: query 与文档无任何 token 重叠时 score=0，该路无结果（依赖向量检索补足）
- 局限: 当前无持久化索引，chunk 数量大时延迟与内存占用随检索线性增长
"""
import re
from typing import Dict, List

from rank_bm25 import BM25Okapi


def tokenize(text: str) -> List[str]:
    """将文本拆分为 BM25 可用的 token 列表。

    当前策略：
    - 拉丁字母/数字：连续片段为一个 token（如 nova、x1、iphone15）
    - 中文：按单字切分（Unicode CJK 范围）

    用法:
    - 调用方: `Bm25Retriever.search()` 对语料与 query 分词
    - 返回值: 小写化后的 token 列表

    TODO:
    - 接入 jieba 中文分词，并配置用户词典（产品型号、业务术语）
    - 英文可考虑 Porter / 词干提取（视语料而定）
    """
    text = (text or "").lower()
    latin = re.findall(r"[a-z0-9]+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    return latin + cjk


class Bm25Retriever:
    """BM25 关键词检索器（内存索引，无状态）。

    每次 `search()` 基于传入的 chunks 临时构建 BM25Okapi 索引，
    不持有跨请求状态，由 `HybridSearchEngine` 注入 chunk 列表后调用。
    """

    def search(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int,
    ) -> List[Dict]:
        """对 chunk 列表执行 BM25 检索，返回得分最高的 Top-K。

        用法:
        - 调用方: `HybridSearchEngine.search()`
        - 参数:
            - query: 用户检索问题
            - chunks: 来自 `VectorStore.fetch_chunks_for_kb()` 的片段列表，
                      每项需含 `content` 字段
            - top_k: 返回条数上限（通常取 `KB_BM25_CANDIDATES`）
        - 返回值: 按 bm25_score 降序的命中列表，附加 `bm25_score`、`source: bm25`
        - 过滤: score <= 0 的片段丢弃（query 与文档无词重叠）

        TODO:
        - 索引落库后改为按 kb_id 查询预建索引，而非每次传入全量 chunks
        - 支持传入 document_id 范围缩小检索域
        """
        if not chunks or not query.strip():
            return []

        corpus_tokens = [tokenize(item["content"]) for item in chunks]
        if not any(corpus_tokens):
            return []

        bm25 = BM25Okapi(corpus_tokens)
        scores = bm25.get_scores(tokenize(query))

        ranked = sorted(
            (
                {
                    **chunk,
                    "bm25_score": float(score),
                    "source": "bm25",
                }
                for chunk, score in zip(chunks, scores)
                if score > 0
            ),
            key=lambda item: item["bm25_score"],
            reverse=True,
        )
        return ranked[:top_k]
