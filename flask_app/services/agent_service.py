"""LangChain Agent 服务 - 管理 Agent 和工具调用"""
import json
from typing import List, Dict, Optional, AsyncGenerator
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from .llm_service import LLMService
from .agent_tools import BaiduSearchTool, create_baidu_search_tool, baidu_search_simple
from ..config import Config


class AgentService:
    """LangChain Agent 服务，管理 Agent 和工具"""
    
    def __init__(self, config: Config, llm_service: LLMService):
        """
        初始化 Agent 服务
        
        Args:
            config: 配置对象
            llm_service: LLM 服务实例
        """
        self.config = config
        self.llm_service = llm_service
        self._agent_executors = {}  # 缓存 Agent 执行器
    
    def _create_tools(self, provider_id: str) -> List:
        """
        创建工具列表
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            工具列表
        """
        tools = []
        
        # 创建百度搜索工具
        baidu_api_key = getattr(self.config, 'BAIDU_SEARCH_API_KEY', None)
        baidu_api_url = getattr(self.config, 'BAIDU_SEARCH_API_URL', None)
        
        if baidu_api_key:
            # 使用完整的 BaiduSearchTool（支持API）
            baidu_tool = create_baidu_search_tool(
                api_key=baidu_api_key,
                api_url=baidu_api_url
            )
        else:
            # 使用简化的搜索工具
            baidu_tool = baidu_search_simple
        
        tools.append(baidu_tool)
        
        # 可以在这里添加更多工具
        # tools.append(calculator_tool)
        # tools.append(weather_tool)
        
        return tools
    
    def _create_agent_prompt(self) -> ChatPromptTemplate:
        """
        创建 Agent 的提示词模板
        
        Returns:
            ChatPromptTemplate 实例
        """
        # ReAct 风格的 Agent 提示词
        # 必须包含所有必需的变量：tools, tool_names, agent_scratchpad, input
        # chat_history 通过 MessagesPlaceholder 传递，但需要确保在调用时正确传递
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能助手，可以使用工具来帮助用户解决问题。

你可以使用的工具：
{tools}

工具名称列表：{tool_names}

使用工具的格式：
Action: 工具名称
Action Input: 工具的输入参数

观察结果后，你可以：
1. 继续使用其他工具获取更多信息
2. 基于已有信息给出最终答案

请用中文回答用户的问题。"""),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return prompt
    
    def _get_agent_executor(self, provider_id: str) -> AgentExecutor:
        """
        获取或创建 Agent 执行器（带缓存）
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            AgentExecutor 实例
        """
        cache_key = provider_id
        
        if cache_key not in self._agent_executors:
            print(f"[Agent] 创建新的 Agent 执行器，provider_id: {provider_id}")
            # 获取 LLM 实例
            llm = self.llm_service.get_llm(provider_id)
            
            # 创建工具列表
            tools = self._create_tools(provider_id)
            print(f"[Agent] 创建了 {len(tools)} 个工具: {[tool.name for tool in tools]}")
            
            # 创建 Agent 提示词（必须包含所有必需的变量）
            prompt = self._create_agent_prompt()
            
            # 创建 ReAct Agent
            # prompt 必须包含：tools, tool_names, agent_scratchpad, input
            agent = create_react_agent(llm, tools, prompt)
            
            # 创建 Agent 执行器
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,  # 开发时启用详细日志
                handle_parsing_errors=True,  # 处理解析错误
                max_iterations=5,  # 最大迭代次数，防止无限循环
                max_execution_time=60  # 最大执行时间（秒）
            )
            
            self._agent_executors[cache_key] = agent_executor
            print(f"[Agent] Agent 执行器创建完成")
        
        return self._agent_executors[cache_key]
    
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
                langchain_messages.append(HumanMessage(content=content))
        
        return langchain_messages
    
    async def stream_agent_chat(
        self,
        messages: List[Dict],
        provider_id: str
    ) -> AsyncGenerator[str, None]:
        """
        流式 Agent 聊天
        
        Args:
            messages: 消息列表，格式为 [{'role': '...', 'content': '...'}, ...]
            provider_id: 模型提供商ID
            
        Yields:
            SSE 格式的数据流
        """
        try:
            # 获取 Agent 执行器
            agent_executor = self._get_agent_executor(provider_id)
            
            # 提取最后一条用户消息
            user_message = None
            chat_history = []
            
            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                if role == 'user':
                    if user_message is None:
                        user_message = content
                    else:
                        # 之前的用户消息作为历史
                        chat_history.append(HumanMessage(content=content))
                elif role == 'assistant':
                    chat_history.append(AIMessage(content=content))
                elif role == 'system':
                    # 系统消息可以忽略或作为提示词的一部分
                    pass
            
            if not user_message:
                yield f"data: {json.dumps({'type': 'error', 'message': '未找到用户消息'})}\n\n"
                return
            
            # 准备 Agent 输入
            agent_input = {
                "input": user_message,
                "chat_history": chat_history
            }
            
            print(f"[Agent] 开始执行 Agent，用户消息: {user_message[:100]}...")
            print(f"[Agent] 历史消息数量: {len(chat_history)}")
            
            # 执行 Agent（流式）
            # 注意：LangChain 0.3 的 AgentExecutor 流式支持有限
            # 这里使用 astream 方法，它会返回中间步骤
            full_content = ""
            
            try:
                # 尝试使用 astream 方法（返回中间步骤）
                async for chunk in agent_executor.astream(agent_input):
                    # chunk 是一个字典，包含中间步骤
                    if isinstance(chunk, dict):
                        # 提取输出内容
                        for key, value in chunk.items():
                            if isinstance(value, dict) and "output" in value:
                                output = value["output"]
                                if output and output != full_content:
                                    # 发送新增的内容
                                    new_content = output[len(full_content):] if len(output) > len(full_content) else output
                                    if new_content:
                                        full_content = output
                                        yield f"data: {json.dumps({'type': 'content', 'content': new_content})}\n\n"
                            elif isinstance(value, str):
                                # 直接是字符串输出
                                if value and value != full_content:
                                    new_content = value[len(full_content):] if len(value) > len(full_content) else value
                                    if new_content:
                                        full_content = value
                                        yield f"data: {json.dumps({'type': 'content', 'content': new_content})}\n\n"
                
                # 如果流式输出为空，使用非流式方法获取最终结果
                if not full_content:
                    result = await agent_executor.ainvoke(agent_input)
                    output = result.get("output", "")
                    if output:
                        full_content = output
                        yield f"data: {json.dumps({'type': 'content', 'content': output})}\n\n"
                
            except Exception as e:
                # 如果流式执行失败，回退到非流式执行
                print(f"流式执行失败，回退到非流式: {e}")
                try:
                    result = await agent_executor.ainvoke(agent_input)
                    output = result.get("output", "")
                    if output:
                        full_content = output
                        yield f"data: {json.dumps({'type': 'content', 'content': output})}\n\n"
                except Exception as e2:
                    error_msg = f"Agent 执行失败: {str(e2)}"
                    yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
                    return
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            error_msg = f"Agent 执行失败: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            raise
    
    def invoke_agent(
        self,
        messages: List[Dict],
        provider_id: str
    ) -> Dict:
        """
        同步调用 Agent（非流式）
        
        Args:
            messages: 消息列表
            provider_id: 模型提供商ID
            
        Returns:
            包含 output 的字典
        """
        try:
            # 获取 Agent 执行器
            agent_executor = self._get_agent_executor(provider_id)
            
            # 提取最后一条用户消息
            user_message = None
            chat_history = []
            
            for msg in messages:
                role = msg.get('role', '')
                content = msg.get('content', '')
                
                if role == 'user':
                    if user_message is None:
                        user_message = content
                    else:
                        chat_history.append(HumanMessage(content=content))
                elif role == 'assistant':
                    chat_history.append(AIMessage(content=content))
            
            if not user_message:
                return {"output": "未找到用户消息", "error": True}
            
            # 准备 Agent 输入
            agent_input = {
                "input": user_message,
                "chat_history": chat_history
            }
            
            # 执行 Agent
            result = agent_executor.invoke(agent_input)
            return result
            
        except Exception as e:
            return {"output": f"Agent 执行失败: {str(e)}", "error": True}
    
    def clear_cache(self, provider_id: Optional[str] = None):
        """
        清理 Agent 执行器缓存
        
        Args:
            provider_id: 如果指定，只清理该提供商的缓存；否则清理所有
        """
        if provider_id:
            self._agent_executors.pop(provider_id, None)
        else:
            self._agent_executors.clear()

