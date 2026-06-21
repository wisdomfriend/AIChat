"""知识库子模块导出。

子模块总览：
- `context`            请求级 ContextVar（Agent 工具读取 user_id / kb_ids）
- `document_extractor` 文档文本提取（txt/md/doc/docx）
- `chunker`            文本分块
- `embedding_client`   Embedding API 客户端
- `vector_store`       PostgreSQL + pgvector 向量存储
- `bm25_retriever`     BM25 关键词检索
- `rerank_client`      Rerank API 客户端
- `hybrid_search`      混合检索引擎（向量 + BM25 + RRF + Rerank）

对外常用导出见 `__all__`；完整业务编排见上层 `KnowledgeService`。
"""
from .context import clear_knowledge_context, get_knowledge_context, set_knowledge_context
from .document_extractor import KB_SUPPORTED_EXTENSIONS, KbDocumentExtractor
from .hybrid_search import HybridSearchEngine

__all__ = [
    "KB_SUPPORTED_EXTENSIONS",
    "KbDocumentExtractor",
    "HybridSearchEngine",
    "set_knowledge_context",
    "get_knowledge_context",
    "clear_knowledge_context",
]
