"""知识库检索上下文 — 供 Agent 工具在请求级读取 user_id / kb_ids。

职责总览：
1) 上下文写入
   - `set_knowledge_context()`  在 Agent 流式请求开始时绑定用户与知识库
2) 上下文读取
   - `get_knowledge_context()`  在 `knowledge_search` 工具内读取当前请求的上下文
3) 上下文清理
   - `clear_knowledge_context()`  请求结束（含异常）时在 finally 中清除

设计说明：
- 使用 Python `ContextVar`，每个 HTTP 请求 / 执行上下文拥有独立副本，并发请求互不干扰
- 避免将 user_id、kb_ids 硬编码进 LangChain 工具闭包，工具定义可在进程级复用

调用链：
  AgentService.run_agent_stream
    → set_knowledge_context(user_id, knowledge_base_ids)
    → agent.stream → knowledge_search 工具
    → get_knowledge_context()
    → finally: clear_knowledge_context()

已知局限与 TODO：
- TODO: 扩展上下文字段（如 top_k、检索模式）供工具读取
- TODO: 与 Flask `g` 对齐的桥接层，便于在路由层直接设置
- 局限: 依赖调用方在 finally 中清理；遗漏清理可能影响同线程后续逻辑上下文
"""
from contextvars import ContextVar
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class KnowledgeSearchContext:
    """单次 Agent 请求的知识库检索上下文。"""

    user_id: int
    knowledge_base_ids: List[int]


_kb_context: ContextVar[Optional[KnowledgeSearchContext]] = ContextVar(
    "kb_search_context", default=None
)


def set_knowledge_context(user_id: int, knowledge_base_ids: Optional[List[int]]) -> None:
    """绑定当前执行上下文的知识库检索参数。

    用法:
    - 调用方: `AgentService.run_agent_stream()` 在 stream 开始前
    - 参数:
        - user_id: 当前登录用户 ID
        - knowledge_base_ids: 前端选中的知识库 ID 列表（可为空）
    """
    ids = [int(i) for i in (knowledge_base_ids or []) if i is not None]
    _kb_context.set(KnowledgeSearchContext(user_id=user_id, knowledge_base_ids=ids))


def get_knowledge_context() -> Optional[KnowledgeSearchContext]:
    """读取当前执行上下文的知识库检索参数。

    用法:
    - 调用方: `agent_tools.knowledge_search` 工具
    - 返回值: 已设置的 `KnowledgeSearchContext`；未设置时返回 None
    """
    return _kb_context.get()


def clear_knowledge_context() -> None:
    """清除当前执行上下文的知识库检索参数。

    用法:
    - 调用方: `AgentService.run_agent_stream()` 的 finally 块
    """
    _kb_context.set(None)
