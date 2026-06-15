"""业务逻辑 Service 层统一导出。

Service 总览（按调用关系）：
1) 认证与统计
   - `AuthService`   登录与注册
   - `StatsService`  Token 用量统计
2) 聊天核心
   - `ChatService`              会话管理与 SSE 流式聊天
   - `LLMService`               多 LLM 提供商管理（单例）
   - `LangChainMemoryManager`   上下文压缩与历史消息
   - `MySQLChatMessageHistory`  LangChain 消息持久化
3) 文件
   - `FileService`  文件上传、文本提取与上下文拼接
"""
from .auth_service import AuthService
from .chat_service import ChatService
from .file_service import FileService
from .langchain_memory_manager import LangChainMemoryManager
from .llm_service import LLMService
from .memory_store import MySQLChatMessageHistory
from .stats_service import StatsService

__all__ = [
    'AuthService',
    'ChatService',
    'StatsService',
    'FileService',
    'LangChainMemoryManager',
    'MySQLChatMessageHistory',
    'LLMService',
]
