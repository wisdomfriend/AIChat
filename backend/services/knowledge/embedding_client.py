"""Embedding API 客户端 — 兼容 OpenAI /v1/embeddings 格式。

职责总览：
1) 配置读取
   - 从 `Config` 加载 API 地址、密钥、模型名、维度、超时
2) 向量化
   - `embed_texts()`  批量将文本转为向量（文档入库时分批调用）
   - `embed_query()`  单条 query 向量化（检索时调用）

在流水线中的位置：
- 入库: `KnowledgeService._process_document()` → embed_texts(chunks)
- 检索: `HybridSearchEngine.search()` → embed_query(query)

相关配置（`Config` / `.env`）：
- `KB_EMBEDDING_API_URL`      可填基础地址 `/v1` 或完整 `/v1/embeddings`
- `KB_EMBEDDING_API_KEY`      API 密钥
- `KB_EMBEDDING_MODEL`        模型名（如 Qwen/Qwen3-Embedding-0.6B）
- `KB_EMBEDDING_DIMENSION`    向量维度，须与 PostgreSQL vector 列及模型一致
- `KB_EMBEDDING_TIMEOUT`      请求超时（秒）

已知局限与 TODO：
- TODO: 按模型自动选择是否传 `dimensions` 参数（仅 Qwen 系列支持）
- TODO: 失败重试与指数退避；区分 429 限流与 4xx 配置错误
- TODO: 本地 Embedding 模型支持（sentence-transformers），减少外部 API 依赖
- TODO: 可配置 `KB_EMBEDDING_BATCH_SIZE`，替代硬编码 `_BATCH_SIZE`
- 局限: 单条文本过长时 API 可能返回 400，需与 `chunker` 块大小协同
- 局限: 维度不匹配时直接抛错，不会自动修正或截断向量
"""
from typing import List

import requests


class EmbeddingClient:
    """OpenAI 兼容 Embedding API 客户端。"""

    _BATCH_SIZE = 8

    def __init__(self, config):
        self.api_url = (config.KB_EMBEDDING_API_URL or "").rstrip("/")
        self.api_key = config.KB_EMBEDDING_API_KEY or ""
        self.model = config.KB_EMBEDDING_MODEL or "embedding"
        self.dimension = config.KB_EMBEDDING_DIMENSION
        self.timeout = config.KB_EMBEDDING_TIMEOUT

    @property
    def enabled(self) -> bool:
        """是否已配置 Embedding API 地址。"""
        return bool(self.api_url)

    @property
    def embeddings_url(self) -> str:
        """解析完整的 embeddings 请求 URL（自动补全 `/embeddings` 后缀）。"""
        if self.api_url.endswith("/embeddings"):
            return self.api_url
        return f"{self.api_url}/embeddings"

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """将多条文本批量向量化。

        用法:
        - 调用方: 文档入库 `KnowledgeService._process_document()`
        - 参数: 文本列表（通常为 chunk 列表）
        - 返回值: 与输入等长的向量列表，每条维度为 `KB_EMBEDDING_DIMENSION`
        - 分批: 每批最多 `_BATCH_SIZE` 条，避免 API 单次 payload 过大
        """
        if not texts:
            return []
        if not self.enabled:
            raise RuntimeError("未配置 KB_EMBEDDING_API_URL，无法向量化文档")

        vectors: List[List[float]] = []
        for start in range(0, len(texts), self._BATCH_SIZE):
            batch = texts[start : start + self._BATCH_SIZE]
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """向 API 发送单批 embedding 请求并校验返回维度。"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {"model": self.model, "input": texts, "dimensions": self.dimension}
        response = requests.post(
            self.embeddings_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if not response.ok:
            detail = response.text[:300]
            raise RuntimeError(
                f"Embedding API 请求失败 ({response.status_code}): {detail}"
            )

        data = response.json()
        items = data.get("data") or []
        if not items:
            raise RuntimeError(f"Embedding API 返回空 data: {data}")

        items.sort(key=lambda item: item.get("index", 0))
        vectors = [item["embedding"] for item in items]
        for vector in vectors:
            if len(vector) != self.dimension:
                raise RuntimeError(
                    f"Embedding 维度不匹配：期望 {self.dimension}，实际 {len(vector)}。"
                    f"请检查 KB_EMBEDDING_DIMENSION 是否与模型一致。"
                )
        return vectors

    def embed_query(self, query: str) -> List[float]:
        """将单条检索问题向量化。

        用法:
        - 调用方: `HybridSearchEngine.search()` → `VectorStore.vector_search()`
        """
        return self.embed_texts([query])[0]
