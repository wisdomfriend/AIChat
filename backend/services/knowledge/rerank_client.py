"""Rerank API 客户端 — 兼容 Jina / 通用 {results:[{index,relevance_score}]} 格式。

职责总览：
1) 配置读取
   - 从 `Config` 加载 Rerank API 地址、密钥、模型名、超时
2) 重排序
   - `rerank()`  根据 query 对候选文档片段重新打分排序

在混合检索中的位置（见 `hybrid_search.py`）：
  向量 + BM25 → RRF 融合 → rerank(top_n) → 最终结果

相关配置（`Config` / `.env`）：
- `KB_RERANK_API_URL`   可填基础地址 `/v1` 或完整 `/v1/rerank`
- `KB_RERANK_API_KEY`   API 密钥
- `KB_RERANK_MODEL`     模型名（如 BAAI/bge-reranker-v2-m3）
- `KB_RERANK_TIMEOUT`   请求超时（秒）

已知局限与 TODO：
- TODO: 未启用时返回按 fusion_score 排序的伪分数，而非固定 0.0
- TODO: 支持 Cohere / Jina 等多厂商响应格式自动适配
- TODO: 失败重试；Rerank 超时后降级为 RRF 结果并记录告警
- TODO: 长文档截断策略（部分 Rerank API 有单条长度上限）
- 局限: `enabled=False` 时返回等权占位分数，由上层决定降级逻辑
- 局限: SiliconFlow 等平台 `document` 字段可能为 null，需兼容解析
"""
from typing import Dict, List

import requests


class RerankClient:
    """OpenAI/Jina 兼容 Rerank API 客户端。"""

    def __init__(self, config):
        self.api_url = (config.KB_RERANK_API_URL or "").rstrip("/")
        self.api_key = config.KB_RERANK_API_KEY or ""
        self.model = config.KB_RERANK_MODEL or "rerank"
        self.timeout = config.KB_RERANK_TIMEOUT

    @property
    def enabled(self) -> bool:
        """是否已配置 Rerank API 地址。"""
        return bool(self.api_url)

    @property
    def rerank_url(self) -> str:
        """解析完整的 rerank 请求 URL（自动补全 `/rerank` 后缀）。"""
        if self.api_url.endswith("/rerank"):
            return self.api_url
        return f"{self.api_url}/rerank"

    def rerank(self, query: str, documents: List[str], top_n: int) -> List[Dict]:
        """对候选文档按与 query 的相关性重排序。

        用法:
        - 调用方: `HybridSearchEngine.search()`
        - 参数:
            - query: 用户检索问题
            - documents: 候选片段纯文本列表（RRF 融合后的 rerank_pool）
            - top_n: 返回条数上限
        - 返回值: `[{ "index": 原文档下标, "relevance_score": 分数 }, ...]`
        - 未启用: 返回前 top_n 条的占位结果（score=0.0），由上层走 hybrid 降级
        """
        if not documents:
            return []
        if not self.enabled:
            return [{"index": i, "relevance_score": 0.0} for i in range(min(top_n, len(documents)))]

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
        }
        response = requests.post(
            self.rerank_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        if not response.ok:
            detail = response.text[:300]
            raise RuntimeError(
                f"Rerank API 请求失败 ({response.status_code}): {detail}"
            )
        data = response.json()

        results = data.get("results")
        if results is None and isinstance(data.get("data"), list):
            results = data["data"]
        if not results:
            raise RuntimeError(f"Rerank API 返回空 results: {data}")

        parsed = []
        for item in results:
            doc = item.get("document") or {}
            parsed.append(
                {
                    "index": int(item.get("index", doc.get("index", 0))),
                    "relevance_score": float(
                        item.get("relevance_score", item.get("score", 0.0))
                    ),
                }
            )
        return parsed
