"""LLM 模型管理 Service（单例）。

职责总览：
1) 实例管理
   - `get_llm()`  获取/缓存 BaseChatOpenAI 实例
   - `get_available_providers()`  返回可用提供商列表
2) 配置
   - `get_provider_config()`  读取指定提供商配置
"""
import threading
from typing import Dict, List

from langchain_core.language_models import BaseChatModel
from langchain_openai.chat_models.base import BaseChatOpenAI


class LLMService:
    """统一管理多个 LLM 提供商，全局单例，跨请求共享模型实例缓存。"""
    
    _instance = None
    _lock = threading.Lock()  # 线程锁，确保线程安全
    
    def __new__(cls, config=None):
        """单例：确保全应用只有一个 LLMService 实例（内部使用）。"""
        if cls._instance is None:
            with cls._lock:
                # 双重检查，避免多线程环境下重复创建
                if cls._instance is None:
                    cls._instance = super(LLMService, cls).__new__(cls)
                    # 初始化操作在 __init__ 中进行
        return cls._instance
    
    def __init__(self, config):
        """初始化 LLM 服务，加载配置（单例仅首次生效）。

        用法:
        - 调用方: `ChatService`、`AgentService`
        - 参数: `config` — Config 实例
        """
        # 避免重复初始化（单例模式下可能被多次调用）
        if hasattr(self, '_initialized'):
            return
        
        self.config = config
        self._llm_instances = {}  # 全局缓存模型实例（跨请求共享）
        self._initialized = True
    
    def get_llm(self, provider_id: str) -> BaseChatModel:
        """获取指定提供商的 BaseChatOpenAI 实例（带缓存）。

        用法:
        - 调用方: 聊天流式生成、Agent 执行
        - 参数: `provider_id` — 如 `deepseek`
        - 返回值: LangChain `BaseChatOpenAI` 实例
        """
        if provider_id not in self._llm_instances:
            self._llm_instances[provider_id] = self._create_llm(provider_id)
        return self._llm_instances[provider_id]
    
    def _create_llm(self, provider_id: str) -> BaseChatOpenAI:
        """
        创建模型实例
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            BaseChatOpenAI 实例
        """
        if provider_id not in self.config.LLM_PROVIDERS:
            raise ValueError(f"不支持的模型提供商: {provider_id}")
        
        provider_config = self.config.LLM_PROVIDERS[provider_id]
        if not provider_config.get('enabled', True):
            raise ValueError(f"模型提供商 {provider_id} 已禁用")
        
        # 获取 API Key
        api_key = self._get_api_key(provider_id)
        
        # OpenAI 兼容 API（DeepSeek 等）使用 BaseChatOpenAI，而非官方 OpenAI 专用的 ChatOpenAI
        # profile.max_input_tokens 供 SummarizationMiddleware 的 fraction 触发使用
        max_context = provider_config.get('max_context_length', 32768)
        llm = BaseChatOpenAI(
            base_url=provider_config['base_url'],
            api_key=api_key,
            model=provider_config['model_name'],
            # temperature=0.7,  # 这里不设置温度,使用后端用户提供的默认值
            streaming=True,
            timeout=600,  # 设置超时时间为 600 秒
            max_retries=2,
            profile={"max_input_tokens": max_context},
        )
        
        return llm
    
    def _get_api_key(self, provider_id: str) -> str:
        """从配置读取 API Key（DeepSeek 来自 DEEPSEEK_API_KEY 环境变量）。"""
        if provider_id not in self.config.LLM_PROVIDERS:
            raise ValueError(f"未知的模型提供商: {provider_id}")
        
        api_key = self.config.LLM_PROVIDERS[provider_id].get('api_key')
        if not api_key:
            raise ValueError("未配置 DeepSeek API Key（请设置 DEEPSEEK_API_KEY 环境变量）")
        return api_key
    
    def get_provider_config(self, provider_id: str) -> Dict:
        """获取指定 LLM 提供商配置（脱敏 api_key）。

        用法:
        - 调用方: 前端展示、调试
        - 参数: `provider_id`
        - 返回值: 配置字典，`api_key` 字段为 `***`
        """
        if provider_id not in self.config.LLM_PROVIDERS:
            raise ValueError(f"不支持的模型提供商: {provider_id}")
        
        provider_config = self.config.LLM_PROVIDERS[provider_id].copy()
        # 不返回敏感信息（api_key）
        if 'api_key' in provider_config:
            provider_config['api_key'] = '***'
        return provider_config
    
    def get_available_providers(self) -> List[Dict]:
        """返回所有已启用的 LLM 提供商列表。

        用法:
        - 调用方: `GET /api/llm/providers`
        - 返回值: `[{ id, name, enabled, supports_images }, ...]`
        """
        providers = []
        for provider_id, config in self.config.LLM_PROVIDERS.items():
            if config.get('enabled', True):
                providers.append({
                    'id': provider_id,
                    'name': config.get('display_name', provider_id),
                    'enabled': True,
                    'supports_images': config.get('supports_images', False)
                })
        return providers


LLM_SERVICE_KEY = "llm_service"


def register_llm_service(app, config) -> LLMService:
    """在应用工厂中注册进程级 LLMService。"""
    service = LLMService(config)
    app.extensions[LLM_SERVICE_KEY] = service
    return service


def get_llm_service() -> LLMService:
    from flask import current_app

    try:
        return current_app.extensions[LLM_SERVICE_KEY]
    except RuntimeError as exc:
        raise RuntimeError("必须在 Flask 应用上下文中访问 LLMService") from exc
    except KeyError as exc:
        raise RuntimeError("LLMService 未初始化，请在 create_app 中调用 register_llm_service") from exc
