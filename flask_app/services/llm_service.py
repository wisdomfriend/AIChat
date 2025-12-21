"""LLM 模型管理器 - 使用 LangChain 统一管理多个 LLM 模型"""
import json
import asyncio
import threading
from typing import List, Dict, Optional, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import tiktoken


class LLMService:
    """LLM 模型管理器，统一管理多个 LLM 提供商（单例模式）"""
    
    _instance = None
    _lock = threading.Lock()  # 线程锁，确保线程安全
    
    def __new__(cls, config=None):
        """
        单例模式实现：确保整个应用只有一个 LLMService 实例
        
        Args:
            config: 配置对象（Config 实例），仅在首次创建时使用
        """
        if cls._instance is None:
            with cls._lock:
                # 双重检查，避免多线程环境下重复创建
                if cls._instance is None:
                    cls._instance = super(LLMService, cls).__new__(cls)
                    # 初始化操作在 __init__ 中进行
        return cls._instance
    
    def __init__(self, config):
        """
        初始化 LLM 服务
        
        Args:
            config: 配置对象（Config 实例）
        """
        # 避免重复初始化（单例模式下可能被多次调用）
        if hasattr(self, '_initialized'):
            return
        
        self.config = config
        self._llm_instances = {}  # 全局缓存模型实例（跨请求共享）
        self._initialized = True
    
    def get_llm(self, provider_id: str):
        """
        获取模型实例（带缓存）
        
        Args:
            provider_id: 模型提供商ID（'deepseek' 或 'vllm'）
            
        Returns:
            ChatOpenAI 实例
        """
        if provider_id not in self._llm_instances:
            self._llm_instances[provider_id] = self._create_llm(provider_id)
        return self._llm_instances[provider_id]
    
    def _create_llm(self, provider_id: str) -> ChatOpenAI:
        """
        创建模型实例
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            ChatOpenAI 实例
        """
        if provider_id not in self.config.LLM_PROVIDERS:
            raise ValueError(f"不支持的模型提供商: {provider_id}")
        
        provider_config = self.config.LLM_PROVIDERS[provider_id]
        if not provider_config.get('enabled', True):
            raise ValueError(f"模型提供商 {provider_id} 已禁用")
        
        # 获取 API Key
        api_key = self._get_api_key(provider_id)
        
        # 创建 LangChain ChatOpenAI 实例
        llm = ChatOpenAI(
            base_url=provider_config['base_url'],
            api_key=api_key,
            model=provider_config['model_name'],
            # temperature=0.7,  # 这里不设置温度,使用后端用户提供的默认值
            streaming=True,
            timeout=600,  # 设置超时时间为 600 秒
            max_retries=2
        )
        
        return llm
    
    def _get_api_key(self, provider_id: str) -> str:
        """
        获取 API Key
        
        DeepSeek: 从数据库读取
        vLLM: 从配置读取
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            API Key
        """
        provider_config = self.config.LLM_PROVIDERS[provider_id]
        
        # DeepSeek 从数据库读取
        if provider_id == 'deepseek':
            from ..database import get_session
            from ..models import ApiKey
            
            db = get_session()
            try:
                api_key_obj = db.query(ApiKey).filter(
                    ApiKey.provider == 'deepseek',
                    ApiKey.is_active == True
                ).first()
                if not api_key_obj:
                    raise ValueError("未配置 DeepSeek API Key")
                return api_key_obj.api_key
            finally:
                db.close()
        
        # vLLM 从配置读取
        elif provider_id == 'vllm':
            api_key = provider_config.get('api_key')
            if not api_key:
                raise ValueError("未配置 vLLM API Key")
            return api_key
        
        else:
            raise ValueError(f"未知的模型提供商: {provider_id}")
    
    def get_max_context_length(self, provider_id: str) -> int:
        """
        获取模型的最大上下文长度
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            最大上下文长度（token 数）
        """
        if provider_id not in self.config.LLM_PROVIDERS:
            raise ValueError(f"不支持的模型提供商: {provider_id}")
        
        provider_config = self.config.LLM_PROVIDERS[provider_id]
        return provider_config.get('max_context_length', 32768)
    
    def count_tokens(self, messages: List[Dict], provider_id: str) -> int:
        """
        计算消息的 token 数
        
        Args:
            messages: 消息列表，格式为 [{'role': '...', 'content': '...'}, ...]
            provider_id: 模型提供商ID（用于选择 tokenizer）
            
        Returns:
            token 数量
        """
        # 获取模型配置
        provider_config = self.config.LLM_PROVIDERS.get(provider_id, {})
        model_name = provider_config.get('model_name', 'gpt-3.5-turbo')
        
        # 使用 tiktoken 计算（默认使用 gpt-3.5-turbo 的编码）
        try:
            encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except KeyError:
            # 如果模型不存在，使用 cl100k_base 编码（GPT-3.5/4 通用）
            encoding = tiktoken.get_encoding("cl100k_base")
        
        # 计算所有消息的 token 数
        total_tokens = 0
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            # 每条消息的格式：role + content + 格式标记
            # 粗略估算：content token + 4（格式标记）
            tokens = len(encoding.encode(content))
            total_tokens += tokens + 4
        
        # 添加系统消息的额外开销
        total_tokens += 2
        
        return total_tokens
    
    def _convert_messages_to_langchain(self, messages: List[Dict]) -> List[BaseMessage]:
        """
        将字典格式消息转换为 LangChain 消息对象
        
        Args:
            messages: 消息列表，格式为 [{'role': '...', 'content': '...'}, ...]
            
        Returns:
            LangChain 消息对象列表
        """
        langchain_messages = []
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'user':
                langchain_messages.append(HumanMessage(content=content))
            elif role == 'assistant':
                langchain_messages.append(AIMessage(content=content))
            elif role == 'system':
                langchain_messages.append(SystemMessage(content=content))
            else:
                # 未知角色，默认作为用户消息
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    async def stream_chat(
        self, 
        messages: List[Dict], 
        provider_id: str
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天，返回 SSE 格式数据
        
        Args:
            messages: 消息列表，格式为 [{'role': '...', 'content': '...'}, ...]
            provider_id: 模型提供商ID
            
        Yields:
            SSE 格式的数据流
        """
        try:
            # 获取模型实例
            llm = self.get_llm(provider_id)
            
            # 转换消息格式
            langchain_messages = self._convert_messages_to_langchain(messages)
            
            # 流式调用
            full_content = ""
            usage = None
            
            async for chunk in llm.astream(langchain_messages):
                # 提取内容
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    full_content += content
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                
                # 尝试提取 usage 信息（可能在响应元数据中）
                if hasattr(chunk, 'response_metadata'):
                    metadata = chunk.response_metadata
                    if metadata and 'usage' in metadata:
                        usage = metadata['usage']
            
            # 发送 usage 信息
            if usage:
                # 使用从流式响应中获取的真实 usage 信息
                yield f"data: {json.dumps({'type': 'usage', 'usage': usage})}\n\n"
            else:
                # 如果流式响应中没有 usage（某些 API 可能不提供），使用 tiktoken 估算
                # 注意：不重新调用 API，避免额外的成本和延迟
                prompt_tokens = self.count_tokens(messages, provider_id)
                completion_tokens = len(tiktoken.get_encoding("cl100k_base").encode(full_content))
                usage = {
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': prompt_tokens + completion_tokens
                }
                yield f"data: {json.dumps({'type': 'usage', 'usage': usage})}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            # 错误处理：区分不同模型的错误
            error_msg = f"[{provider_id}] 模型调用失败: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            raise
    
    def get_provider_config(self, provider_id: str) -> Dict:
        """
        获取模型提供商配置
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            配置字典
        """
        if provider_id not in self.config.LLM_PROVIDERS:
            raise ValueError(f"不支持的模型提供商: {provider_id}")
        
        provider_config = self.config.LLM_PROVIDERS[provider_id].copy()
        # 不返回敏感信息（api_key）
        if 'api_key' in provider_config:
            provider_config['api_key'] = '***'
        return provider_config
    
    def get_available_providers(self) -> List[Dict]:
        """
        获取所有可用的模型提供商列表
        
        Returns:
            提供商列表，格式为 [{'id': '...', 'name': '...', 'enabled': True}, ...]
        """
        providers = []
        for provider_id, config in self.config.LLM_PROVIDERS.items():
            if config.get('enabled', True):
                providers.append({
                    'id': provider_id,
                    'name': config.get('display_name', provider_id),
                    'enabled': True
                })
        return providers
    
    def clear_cache(self, provider_id: Optional[str] = None):
        """
        清理模型实例缓存
        
        Args:
            provider_id: 如果指定，只清理该提供商的缓存；否则清理所有
        """
        if provider_id:
            self._llm_instances.pop(provider_id, None)
        else:
            self._llm_instances.clear()

