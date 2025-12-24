"""Agent 服务 - 提供 ReAct 和 Plan-and-Execute Agent"""
import json
import asyncio
import threading
from queue import Queue
from typing import List, Dict, Optional, AsyncGenerator
from langchain.agents import create_agent
from langchain_core.tools import Tool, StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain_experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
from .agent_tools import calculate, get_time_info
from .llm_service import LLMService

# 尝试导入 AgentExecutor（可能在 langchain_core 或其他位置）
try:
    from langchain.agents import AgentExecutor
except ImportError:
    try:
        from langchain_core.agents import AgentExecutor
    except ImportError:
        # 如果找不到 AgentExecutor，使用类型提示
        AgentExecutor = None


class AgentService:
    """Agent 服务类"""
    
    def __init__(self, config):
        """
        初始化 Agent 服务
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.llm_service = LLMService(config)
        
        # 创建工具列表
        self.tools = self._create_tools()
    
    def _create_tools(self) -> List[Tool]:
        """
        创建工具列表
        
        Returns:
            工具列表
        """
        tools = [
            StructuredTool.from_function(
                func=get_time_info,
                name="get_time_info",
                description="获取详细的时间信息，包括日期、时间、星期等。不需要参数。"
            )
        ]
        return tools
    
    def create_react_agent(self, provider_id: str):
        """
        创建 ReAct Agent
        
        Args:
            provider_id: 模型提供商ID
            
        Returns:
            Agent 包装器实例
        """
        llm = self.llm_service.get_llm(provider_id)
        
        # 创建系统提示词
        system_prompt = """你是一个智能助手，可以使用工具来回答问题。

你可以使用的工具：
- get_time_info: 获取详细的时间信息

使用工具时，请遵循以下步骤：
1. 思考：分析用户问题，确定需要调用哪些工具
2. 行动：调用相应的工具
3. 观察：查看工具返回的结果
4. 思考：根据结果继续思考或给出最终答案

请用中文回答用户的问题。"""
        
        # 使用 create_agent 创建 ReAct Agent（LangChain 1.2.0+）
        # create_agent 的第一个参数是 model，不是 llm
        # 它返回一个 CompiledStateGraph
        agent_graph = create_agent(
            model=llm,
            tools=self.tools,
            system_prompt=system_prompt
        )
        
        # create_agent 返回的是 CompiledStateGraph，需要包装以支持我们的接口
        class AgentWrapper:
            def __init__(self, agent_graph, tools):
                self.agent_graph = agent_graph
                self.tools = tools
                self.verbose = True
                self.handle_parsing_errors = True
                self.return_intermediate_steps = True
            
            def invoke(self, input_data):
                # create_agent 返回的 graph 使用 messages 格式
                # 如果输入是字典且包含 input 和 chat_history，需要转换
                if isinstance(input_data, dict):
                    if "input" in input_data:
                        # 转换格式：input + chat_history -> messages
                        messages = []
                        if "chat_history" in input_data:
                            messages.extend(input_data["chat_history"])
                        messages.append(HumanMessage(content=input_data["input"]))
                        graph_input = {"messages": messages}
                    elif "messages" in input_data:
                        graph_input = input_data
                    else:
                        # 如果格式不对，尝试直接使用
                        graph_input = input_data
                else:
                    graph_input = {"messages": [HumanMessage(content=str(input_data))]}
                
                # 调用 graph
                result = self.agent_graph.invoke(graph_input)
                
                # 提取结果
                # result 应该包含 messages 列表
                if isinstance(result, dict) and "messages" in result:
                    messages = result["messages"]
                    # 找到最后一条 AI 消息
                    output = ""
                    intermediate_steps = []
                    
                    for msg in messages:
                        if hasattr(msg, 'content') and msg.content:
                            if isinstance(msg, AIMessage):
                                output = msg.content
                            elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                                # 提取工具调用信息
                                for tool_call in msg.tool_calls:
                                    intermediate_steps.append((
                                        type('Action', (), {'tool': tool_call.get('name', 'unknown'), 'tool_input': tool_call.get('args', {})})(),
                                        "工具调用"
                                    ))
                    
                    return {
                        "output": output,
                        "intermediate_steps": intermediate_steps
                    }
                else:
                    # 如果格式不对，尝试提取字符串
                    return {
                        "output": str(result) if result else "",
                        "intermediate_steps": []
                    }
        
        return AgentWrapper(agent_graph, self.tools)
    
    def create_plan_execute_agent(self, provider_id: str):
        """
        创建 Plan-and-Execute Agent
        
        Args:
            provider_id: 模型提供商ID（此参数保留以保持接口一致性，但实际使用 openai-3.5-turbo）
            
        Returns:
            PlanAndExecute 实例
        """
        # 写死使用 openai-3.5-turbo 模型（支持 stop 参数） TODO gpt-5.2 不支持这个参数
        llm = self.llm_service.get_llm('openai-3.5-turbo')
        
        # 创建规划器和执行器
        try:
            planner = load_chat_planner(llm)
        except Exception as e:
            print(f"load_chat_planner failed: {e}")
            raise
        
        try:
            executor = load_agent_executor(llm, self.tools, verbose=True)
        except Exception as e:
            print(f"load_agent_executor failed: {e}")
            raise ValueError(f"无法创建 executor: {e}")
        
        # 创建 Plan-and-Execute Agent
        agent = PlanAndExecute(
            planner=planner,
            executor=executor,
            verbose=True
        )
        
        return agent
    
    async def run_react_agent_stream(
        self,
        provider_id: str,
        user_input: str,
        chat_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式运行 ReAct Agent
        
        Args:
            provider_id: 模型提供商ID
            user_input: 用户输入
            chat_history: 聊天历史（可选）
            
        Yields:
            SSE 格式的数据流
        """
        try:
            # 创建 Agent
            agent_executor = self.create_react_agent(provider_id)
            
            # 转换聊天历史为 LangChain 消息格式
            langchain_messages = []
            if chat_history:
                for msg in chat_history:
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role == 'user':
                        langchain_messages.append(HumanMessage(content=content))
                    elif role == 'assistant':
                        langchain_messages.append(AIMessage(content=content))
            
            # 准备输入
            input_messages = langchain_messages + [HumanMessage(content=user_input)]
            result = agent_executor.invoke({"messages": input_messages})
            
            # 发送中间步骤（思考轨迹）
            if "intermediate_steps" in result:
                for step in result["intermediate_steps"]:
                    action = step[0]
                    observation = step[1]
                    
                    # 发送工具调用信息
                    tool_name = action.tool if hasattr(action, 'tool') else "未知工具"
                    tool_input = action.tool_input if hasattr(action, 'tool_input') else {}
                    
                    yield f"data: {json.dumps({'type': 'agent_think', 'content': f'思考：需要使用工具 {tool_name}'})}\n\n"
                    yield f"data: {json.dumps({'type': 'agent_action', 'content': f'行动：调用工具 {tool_name}，参数：{tool_input}'})}\n\n"
                    yield f"data: {json.dumps({'type': 'agent_observation', 'content': f'观察：{observation}'})}\n\n"
            
            # 发送最终结果
            output = result.get("output", "")
            if output:
                # 将输出分块发送（模拟流式）
                words = output.split()
                for i, word in enumerate(words):
                    content = word + (" " if i < len(words) - 1 else "")
                    yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            error_msg = f"Agent 执行错误: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            raise
    
    async def run_plan_execute_agent_stream(
        self,
        provider_id: str,
        user_input: str,
        chat_history: List[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式运行 Plan-and-Execute Agent
        
        Args:
            provider_id: 模型提供商ID
            user_input: 用户输入
            chat_history: 聊天历史（可选）
            
        Yields:
            SSE 格式的数据流
        """
        try:
            # 创建 Agent
            agent = self.create_plan_execute_agent(provider_id)
            
            # Plan-and-Execute Agent 的 invoke 方法不支持流式输出
            # 我们需要手动处理
            yield f"data: {json.dumps({'type': 'agent_think', 'content': '正在规划任务...'})}\n\n"
            
            # 使用队列来实时传递消息
            message_queue = Queue()
            execution_done = threading.Event()
            result_container = {'result': None, 'error': None}
            
            # 创建自定义 callback 来实时捕获执行步骤
            class StepCallback(BaseCallbackHandler):
                def __init__(self, queue):
                    self.queue = queue
                    self.current_step_num = 0
                    self.in_execution = False
                
                def on_chain_start(self, serialized, inputs, **kwargs):
                    # 修复：serialized 可能为 None
                    if serialized is None:
                        return
                    # 修复：inputs 可能为 None
                    if inputs is None:
                        inputs = {}
                    
                    chain_name = str(serialized.get("name", "")) if isinstance(serialized, dict) else str(serialized)
                    if "AgentExecutor" in chain_name:
                        self.in_execution = True
                        self.current_step_num += 1
                        step_input = inputs.get('input', str(inputs))[:150] if isinstance(inputs, dict) else str(inputs)[:150]
                        # 实时发送消息
                        self.queue.put({
                            'type': 'agent_execute_step',
                            'content': f'开始执行步骤 {self.current_step_num}: {step_input}...',
                            'step_num': self.current_step_num
                        })
                
                def on_agent_action(self, action, **kwargs):
                    tool_name = action.tool if hasattr(action, 'tool') else "未知工具"
                    tool_input = action.tool_input if hasattr(action, 'tool_input') else {}
                    tool_input_str = str(tool_input)[:150] if tool_input else ""
                    # 实时发送消息
                    self.queue.put({
                        'type': 'agent_action',
                        'content': f'调用工具：{tool_name}，参数：{tool_input_str}'
                    })
                
                def on_tool_end(self, output, **kwargs):
                    output_str = str(output)[:200] if output else ""
                    # 实时发送消息
                    self.queue.put({
                        'type': 'agent_observation',
                        'content': f'工具返回：{output_str}'
                    })
                
                def on_chain_end(self, outputs, **kwargs):
                    if self.in_execution:
                        # 实时发送消息
                        self.queue.put({
                            'type': 'agent_execute_step',
                            'content': f'步骤 {self.current_step_num} 完成',
                            'step_num': self.current_step_num
                        })
                        self.in_execution = False
            
            # 创建 callback 实例
            callback = StepCallback(message_queue)
            
            # 改进：在执行时确保原始问题被包含在上下文中
            # Plan-and-Execute Agent 在执行每个步骤时可能会丢失原始问题上下文
            # 我们在输入中明确包含原始问题，让执行器能看到
            enhanced_input = f"用户原始问题：{user_input}\n\n请根据上述问题执行以下步骤。"
            
            # 用于标记规划步骤是否已发送
            plan_sent = threading.Event()
            
            # 在单独线程中执行 Agent（避免阻塞）
            def execute_agent():
                # 启动一个线程来监控规划步骤
                def monitor_plan():
                    import time
                    max_wait = 30  # 最多等待30秒
                    start_time = time.time()
                    while time.time() - start_time < max_wait:
                        if hasattr(agent, 'plan') and agent.plan and not plan_sent.is_set():
                            # 提取并发送规划步骤
                            plan_steps = []
                            try:
                                plan_obj = agent.plan
                                if hasattr(plan_obj, 'steps'):
                                    plan_steps = plan_obj.steps
                                elif isinstance(plan_obj, list):
                                    plan_steps = plan_obj
                                elif hasattr(plan_obj, '__iter__') and not isinstance(plan_obj, str):
                                    try:
                                        plan_steps = list(plan_obj)
                                    except:
                                        pass
                                
                                if not plan_steps and hasattr(plan_obj, '__dict__'):
                                    for attr_name in ['steps', 'plan_steps', '_steps']:
                                        if hasattr(plan_obj, attr_name):
                                            attr_value = getattr(plan_obj, attr_name)
                                            if attr_value:
                                                plan_steps = attr_value if isinstance(attr_value, list) else [attr_value]
                                                break
                            except Exception as e:
                                print(f"提取规划步骤失败: {e}")
                            
                            # 发送规划步骤（如果提取成功）
                            if plan_steps:
                                message_queue.put({
                                    'type': 'agent_plan',
                                    'content': f'规划完成，共 {len(plan_steps)} 个步骤'
                                })
                                for i, step in enumerate(plan_steps, 1):
                                    try:
                                        step_value = None
                                        if hasattr(step, 'value'):
                                            step_value = step.value
                                        elif hasattr(step, 'content'):
                                            step_value = step.content
                                        elif isinstance(step, str):
                                            step_value = step
                                        elif hasattr(step, '__dict__'):
                                            step_dict = step.__dict__
                                            step_value = step_dict.get('value') or step_dict.get('content') or str(step)
                                        else:
                                            step_value = str(step)
                                        
                                        message_queue.put({
                                            'type': 'agent_plan_step',
                                            'content': f'步骤 {i}: {step_value}',
                                            'step_num': i
                                        })
                                    except Exception as e:
                                        print(f"处理规划步骤 {i} 失败: {e}")
                                        message_queue.put({
                                            'type': 'agent_plan_step',
                                            'content': f'步骤 {i}: {str(step)}',
                                            'step_num': i
                                        })
                                plan_sent.set()
                                return
                        time.sleep(0.1)  # 每100ms检查一次
                
                # 启动监控线程
                monitor_thread = threading.Thread(target=monitor_plan, daemon=True)
                monitor_thread.start()
                
                try:
                    result = agent.invoke({"input": enhanced_input}, config={"callbacks": [callback]})
                    result_container['result'] = result
                    
                    # 执行完成后，如果规划步骤还没有发送，再次尝试提取并发送
                    if hasattr(agent, 'plan') and agent.plan and not plan_sent.is_set():
                        plan_steps = []
                        try:
                            plan_obj = agent.plan
                            if hasattr(plan_obj, 'steps'):
                                plan_steps = plan_obj.steps
                            elif isinstance(plan_obj, list):
                                plan_steps = plan_obj
                            elif hasattr(plan_obj, '__iter__') and not isinstance(plan_obj, str):
                                try:
                                    plan_steps = list(plan_obj)
                                except:
                                    pass
                            
                            if not plan_steps and hasattr(plan_obj, '__dict__'):
                                for attr_name in ['steps', 'plan_steps', '_steps']:
                                    if hasattr(plan_obj, attr_name):
                                        attr_value = getattr(plan_obj, attr_name)
                                        if attr_value:
                                            plan_steps = attr_value if isinstance(attr_value, list) else [attr_value]
                                            break
                        except Exception as e:
                            print(f"提取规划步骤失败: {e}")
                        
                        # 发送规划步骤（如果提取成功）
                        if plan_steps:
                            message_queue.put({
                                'type': 'agent_plan',
                                'content': f'规划完成，共 {len(plan_steps)} 个步骤'
                            })
                            for i, step in enumerate(plan_steps, 1):
                                try:
                                    step_value = None
                                    if hasattr(step, 'value'):
                                        step_value = step.value
                                    elif hasattr(step, 'content'):
                                        step_value = step.content
                                    elif isinstance(step, str):
                                        step_value = step
                                    elif hasattr(step, '__dict__'):
                                        step_dict = step.__dict__
                                        step_value = step_dict.get('value') or step_dict.get('content') or str(step)
                                    else:
                                        step_value = str(step)
                                    
                                    message_queue.put({
                                        'type': 'agent_plan_step',
                                        'content': f'步骤 {i}: {step_value}',
                                        'step_num': i
                                    })
                                except Exception as e:
                                    print(f"处理规划步骤 {i} 失败: {e}")
                                    message_queue.put({
                                        'type': 'agent_plan_step',
                                        'content': f'步骤 {i}: {str(step)}',
                                        'step_num': i
                                    })
                except Exception as e:
                    result_container['error'] = e
                finally:
                    execution_done.set()
                    # 发送结束标记
                    message_queue.put(None)
            
            # 启动执行线程
            execution_thread = threading.Thread(target=execute_agent, daemon=True)
            execution_thread.start()
            
            # 实时消费队列中的消息
            while True:
                try:
                    # 等待消息，最多等待0.1秒
                    try:
                        msg = message_queue.get(timeout=0.1)
                        if msg is None:  # 结束标记
                            break
                        # 实时发送消息
                        yield f"data: {json.dumps(msg)}\n\n"
                    except:
                        # 超时，检查是否执行完成
                        if execution_done.is_set():
                            # 再尝试获取一次消息
                            try:
                                while True:
                                    msg = message_queue.get_nowait()
                                    if msg is None:
                                        break
                                    yield f"data: {json.dumps(msg)}\n\n"
                            except:
                                pass
                            break
                        # 继续等待
                        await asyncio.sleep(0.05)
                        continue
                except Exception as e:
                    print(f"处理消息队列错误: {e}")
                    break
            
            # 等待执行完成
            execution_thread.join(timeout=300)  # 最多等待5分钟
            
            # 检查是否有错误
            if result_container['error']:
                raise result_container['error']
            
            result = result_container['result']
            
            # 注意：规划步骤和执行步骤信息已经在执行过程中通过队列实时发送了
            # 这里只需要处理最终结果
            
            # 发送执行结果（最终答案）
            # 注意：Plan-and-Execute 的 result 可能包含多个步骤的结果，我们只显示最终答案
            if result:
                # 将结果转换为字符串
                if isinstance(result, dict):
                    # 如果 result 是字典，尝试提取 output 或 messages
                    if 'output' in result:
                        result_str = str(result['output'])
                    elif 'messages' in result:
                        # 提取最后一条消息的内容
                        messages = result['messages']
                        if messages:
                            last_msg = messages[-1]
                            if hasattr(last_msg, 'content'):
                                result_str = str(last_msg.content)
                            else:
                                result_str = str(last_msg)
                        else:
                            result_str = str(result)
                    else:
                        result_str = str(result)
                else:
                    result_str = str(result)
                
                # 检查 result_str 是否包含 JSON 格式的 Final Answer
                # 如果包含，提取其中的 action_input 内容，避免显示 JSON 格式
                if result_str and 'Final Answer' in result_str and 'action_input' in result_str:
                    try:
                        # 尝试解析 JSON 格式的 Final Answer
                        import re
                        # 查找 action_input 字段的内容（支持多行和转义字符）
                        # 匹配 "action_input": "..." 格式
                        match = re.search(r'"action_input"\s*:\s*"((?:[^"\\]|\\.)*)"', result_str, re.DOTALL)
                        if match:
                            # 提取 action_input 的内容（去除转义字符）
                            extracted_content = match.group(1)
                            # 处理转义字符
                            extracted_content = extracted_content.replace('\\n', '\n').replace('\\"', '"').replace('\\t', '\t')
                            result_str = extracted_content
                    except Exception as e:
                        print(f"解析 Final Answer 失败: {e}")
                        # 如果解析失败，继续使用原始 result_str
                
                # 将结果分块发送（模拟流式，按字符发送）
                if result_str:
                    chunk_size = 10  # 每次发送10个字符
                    for i in range(0, len(result_str), chunk_size):
                        chunk = result_str[i:i+chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            error_msg = f"Agent 执行错误: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            raise

