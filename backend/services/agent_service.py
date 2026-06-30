"""Agent Service — 基于 create_agent 的统一对话引擎。"""
import json
from typing import Dict, Generator, List, Optional

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .agent_tools import build_agent_tools
from .checkpointer_service import get_checkpointer
from .knowledge_service import KnowledgeService
from .llm_service import LLMService
from .web_search_service import WebSearchService

SYSTEM_PROMPT = """你是一个友好、专业且乐于助人的 AI 助手。

你可以使用以下工具：
- knowledge_search：检索用户选择的知识库（内部文档、制度、项目资料等）
- web_search：搜索互联网，获取新闻、价格、天气等实时信息
- get_time_info：获取当前时间

规则：
1. 用户已选择知识库时，涉及文档/内部资料的问题优先调用 knowledge_search，不要编造
2. 需要实时或最新信息时，主动调用 web_search，不要编造
3. 用户问时间、日期时，调用 get_time_info
4. 用简洁清晰的中文回答；不确定时请诚实说明
5. 用户上传的文件内容已在消息中，请基于文件内容作答"""


class AgentService:
    """封装 create_agent 创建、checkpoint bootstrap 与 SSE 流式执行。"""

    def __init__(self, config, llm_service=None):
        self.config = config
        self.llm_service = llm_service or LLMService(config)
        self.search_service = WebSearchService(config)
        self.knowledge_service = KnowledgeService(config)
        self._agents: Dict[str, object] = {}

    def _create_agent(self, provider_id: str):
        llm = self.llm_service.get_llm(provider_id)
        tools = build_agent_tools(self.search_service, self.knowledge_service)
        checkpointer = get_checkpointer()
        middleware = [
            SummarizationMiddleware(
                model=llm,
                trigger=("fraction", self.config.AGENT_SUMMARY_TRIGGER_FRACTION),
                keep=("messages", self.config.AGENT_SUMMARY_KEEP_MESSAGES),
            )
        ]
        return create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
            middleware=middleware,
        )

    def get_agent(self, provider_id: str):
        if provider_id not in self._agents:
            self._agents[provider_id] = self._create_agent(provider_id)
        return self._agents[provider_id]

    def _agent_config(self, session_id: int) -> dict:
        return {
            "configurable": {"thread_id": str(session_id)},
            "recursion_limit": self.config.AGENT_RECURSION_LIMIT,
        }

    def bootstrap_checkpoint_if_needed(self, agent, session_id: int, seed_messages: List) -> None:
        """若 PG 无 checkpoint，用 MySQL 历史 seed。"""
        config = self._agent_config(session_id)
        state = agent.get_state(config)
        existing = (state.values or {}).get("messages") or []
        if existing:
            return
        if seed_messages:
            agent.update_state(config, {"messages": seed_messages})

    def run_agent_stream(
            self,
            provider_id: str,
            session_id: int,
            user_message: HumanMessage,
            seed_messages: Optional[List] = None,
            user_id: Optional[int] = None,
            knowledge_base_ids: Optional[List[int]] = None,
    ) -> Generator[str, None, None]:
        """流式运行 Agent，yield SSE 事件。"""
        from .knowledge.context import clear_knowledge_context, set_knowledge_context

        if user_id is not None:
            set_knowledge_context(user_id, knowledge_base_ids)

        agent = self.get_agent(provider_id)
        config = self._agent_config(session_id)

        self.bootstrap_checkpoint_if_needed(agent, session_id, seed_messages or [])

        assistant_content = ""
        tool_calls_log: List[Dict] = []
        usage = None
        pending_tools: Dict[str, Dict] = {}

        try:
            for mode, chunk in agent.stream(
                    {"messages": [user_message]},
                    config=config,
                    stream_mode=["messages", "updates", "custom"],
            ):
                if mode == "messages":
                    token, _metadata = chunk
                    content = getattr(token, "content", None)
                    if not content or not isinstance(content, str):
                        continue
                    if getattr(token, "tool_calls", None):
                        continue
                    if isinstance(token, ToolMessage):
                        continue
                    assistant_content += content
                    yield f"data: {json.dumps({'type': 'content', 'content': content}, ensure_ascii=False)}\n\n"

                elif mode == "updates":
                    for _node, update in chunk.items():
                        if not isinstance(update, dict):
                            continue
                        for msg in update.get("messages", []):
                            yield from self._events_from_update_message(
                                msg, tool_calls_log, pending_tools
                            )

                elif mode == "custom":
                    payload = chunk
                    if isinstance(payload, dict):
                        yield f"data: {json.dumps({'type': 'tool_status', **payload}, ensure_ascii=False)}\n\n"

            final_state = agent.get_state(config)
            for msg in reversed((final_state.values or {}).get("messages", [])):
                if isinstance(msg, AIMessage) and msg.content and not assistant_content:
                    assistant_content = msg.content if isinstance(msg.content, str) else str(msg.content)
                if isinstance(msg, AIMessage) and getattr(msg, "usage_metadata", None):
                    um = msg.usage_metadata
                    usage = {
                        "prompt_tokens": um.get("input_tokens", 0),
                        "completion_tokens": um.get("output_tokens", 0),
                        "total_tokens": um.get("total_tokens", 0),
                    }
                    break

            if usage:
                yield f"data: {json.dumps({'type': 'usage', 'usage': usage}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'tool_calls': tool_calls_log}, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_msg = f"Agent 执行错误: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg}, ensure_ascii=False)}\n\n"
            raise
        finally:
            clear_knowledge_context()

    @staticmethod
    def _events_from_update_message(
            msg,
            tool_calls_log: List[Dict],
            pending_tools: Dict[str, Dict],
    ) -> Generator[str, None, None]:
        """从 updates 流解析 tool 事件。"""
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                tc_id = tc.get("id") or tc.get("name", "unknown")
                entry = {
                    "id": tc_id,
                    "name": tc.get("name", "unknown"),
                    "args": tc.get("args", {}),
                }
                pending_tools[tc_id] = entry
                yield f"data: {json.dumps({'type': 'tool_start', 'tool': entry['name'], 'args': entry['args']}, ensure_ascii=False)}\n\n"

        elif isinstance(msg, ToolMessage):
            tc_id = msg.tool_call_id
            entry = pending_tools.pop(tc_id, {"name": msg.name or "tool", "args": {}})
            preview = (msg.content or "")[:200]
            log_entry = {
                "name": entry.get("name") or msg.name,
                "args": entry.get("args", {}),
                "result_preview": preview,
            }
            tool_calls_log.append(log_entry)
            yield f"data: {json.dumps({'type': 'tool_end', 'tool': log_entry['name'], 'result_preview': preview}, ensure_ascii=False)}\n\n"


AGENT_SERVICE_KEY = "agent_service"


def register_agent_service(app, config, llm_service) -> AgentService:
    """在应用工厂中注册进程级 AgentService。"""
    service = AgentService(config, llm_service=llm_service)
    app.extensions[AGENT_SERVICE_KEY] = service
    return service


def get_agent_service() -> AgentService:
    from flask import current_app

    try:
        return current_app.extensions[AGENT_SERVICE_KEY]
    except RuntimeError as exc:
        raise RuntimeError("必须在 Flask 应用上下文中访问 AgentService") from exc
    except KeyError as exc:
        raise RuntimeError("AgentService 未初始化，请在 create_app 中调用 register_agent_service") from exc
