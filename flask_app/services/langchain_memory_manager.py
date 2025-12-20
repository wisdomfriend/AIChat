"""LangChain Memory 管理器 - 支持多种 Memory 类型"""
from typing import List, Dict, Optional, Literal

# LangChain 0.3+ 版本导入
from langchain.memory import (
    ConversationBufferWindowMemory,
    ConversationTokenBufferMemory,
    ConversationSummaryMemory
)

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from .memory_store import MySQLChatMessageHistory
from .file_service import FileService


class LangChainMemoryManager:
    """LangChain Memory 管理器，支持多种 Memory 类型"""
    
    def __init__(
        self,
        session_id: int,
        user_id: int,
        memory_type: Literal['buffer_window', 'token_buffer', 'summary'] = 'token_buffer',
        **memory_kwargs
    ):
        """
        初始化
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            memory_type: Memory类型
                - 'buffer_window': 固定窗口大小
                - 'token_buffer': 基于token限制
                - 'summary': 摘要模式
            **memory_kwargs: Memory的额外参数
                - buffer_window: {'k': 10}  # 保留最近k轮对话
                - token_buffer: {'max_token_limit': 4000}  # 最大token数
                - summary: {'llm': ...}  # 用于摘要的LLM
        """
        self.session_id = session_id
        self.user_id = user_id
        self.memory_type = memory_type
        
        # 创建消息历史存储
        self.message_history = MySQLChatMessageHistory(session_id, user_id)
        
        # 创建 Memory 实例
        self.memory = self._create_memory(memory_type, memory_kwargs)
        
        # 文件服务（用于处理文件上下文）
        self.file_service = FileService()
    
    def _create_memory(self, memory_type: str, memory_kwargs: dict):
        """创建 Memory 实例"""
        if memory_type == 'buffer_window':
            k = memory_kwargs.get('k', 10)  # 默认保留最近10条消息
            # 返回 ConversationBufferWindowMemory 实例
            # 
            # 返回对象的使用方式：
            # 1. memory.load_memory_variables({}) 
            #    返回格式: Dict[str, List[BaseMessage]]
            #    例如: {'history': [HumanMessage(...), AIMessage(...), ...]}
            # 
            # 2. 消息对象类型：
            #    - HumanMessage(content="用户消息内容")  # 用户消息
            #    - AIMessage(content="AI回复内容")        # AI消息
            #    - SystemMessage(content="系统消息")     # 系统消息
            # 
            # 3. 每个消息对象都有 content 属性，可通过 msg.content 获取消息内容
            # 
            # 4. 窗口限制说明（重要）：
            #    - k 参数是按消息轮数计算的
            #    - 1 轮对话 = 1 条用户消息 + 1 条 AI 回复 = 2 条消息
            #    - SystemMessage 也会被计入 k 的计数（如果历史中存在）
            #    - 注意：当前代码中 system_prompt 不会保存到数据库
            return ConversationBufferWindowMemory(
                chat_memory=self.message_history,
                k=k,
                return_messages=True
            )
        
        elif memory_type == 'token_buffer':
            max_token_limit = memory_kwargs.get('max_token_limit', 4000)
            # Token buffer memory 需要 LLM 来计算 token
            # 注意：当前代码中未传入 llm 参数，所以会回退到 buffer_window 模式
            # 如果需要使用 token_buffer 模式，需要：
            # 1. 创建 LLM 实例（如 ChatOpenAI 或自定义的 DeepSeek LLM）
            # 2. 在 memory_kwargs 中传入 llm 参数
            # 3. ConversationTokenBufferMemory 内部使用 LLM 的 tokenizer 来计算 token 数量
            # 如果 DeepSeek 使用不同的 tokenizer，可能需要自定义 LLM 类
            llm = memory_kwargs.get('llm')
            if llm is None:
                # 如果没有提供 LLM，回退到 buffer_window
                print(f"Warning: Token buffer memory requires LLM, but llm is None. Falling back to buffer_window mode.")
                return ConversationBufferWindowMemory(
                    chat_memory=self.message_history,
                    k=10,
                    return_messages=True
                )
            
            try:
                return ConversationTokenBufferMemory(
                    chat_memory=self.message_history,
                    max_token_limit=max_token_limit,
                    llm=llm,
                    return_messages=True
                )
            except Exception as e:
                print(f"Warning: Token buffer memory creation failed: {e}, falling back to buffer window")
                return ConversationBufferWindowMemory(
                    chat_memory=self.message_history,
                    k=10,
                    return_messages=True
                )
        
        elif memory_type == 'summary':
            llm = memory_kwargs.get('llm')
            if llm is None:
                raise ValueError("Summary memory requires an LLM instance")
            
            return ConversationSummaryMemory(
                llm=llm,
                chat_memory=self.message_history,
                return_messages=True
            )
        
        else:
            raise ValueError(f"Unsupported memory type: {memory_type}")
    
    def load_memory_variables(self) -> Dict[str, List[BaseMessage]]:
        """加载内存变量（历史消息）"""
        return self.memory.load_memory_variables({})
    
    def get_history_messages(self) -> List[BaseMessage]:
        """获取历史消息列表"""
        memory_vars = self.load_memory_variables()
        return memory_vars.get('history', [])
    
    def get_history_messages_as_dict(self, include_files: bool = True) -> List[Dict]:
        """
        获取历史消息列表（字典格式，兼容现有代码）
        
        Args:
            include_files: 是否包含文件信息
        """
        # 从 LangChain Memory 获取消息
        messages = self.get_history_messages()
        
        # 如果需要包含文件信息，从数据库加载文件信息
        if include_files:
            from ..database import get_session
            from ..models import ChatMessage
            import json
            from .file_service import FileService
            
            db = get_session()
            try:
                # 从数据库加载所有消息（用于获取文件信息）
                db_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == self.session_id
                ).order_by(ChatMessage.created_at.asc()).all()
                
                # 创建消息内容到文件信息的映射
                # 使用 (role, content) 作为key，因为同一会话中相同内容的消息应该很少
                msg_file_map = {}
                file_service = FileService()
                for db_msg in db_messages:
                    if db_msg.file_ids and db_msg.role == 'user':
                        try:
                            file_ids = json.loads(db_msg.file_ids)
                            if file_ids:
                                files = []
                                for fid in file_ids:
                                    file_info = file_service.get_file(fid, self.user_id)
                                    if file_info:
                                        files.append({
                                            'id': file_info['id'],
                                            'filename': file_info['original_filename'],
                                            'file_size': file_info['file_size'],
                                            'file_extension': file_info['file_extension']
                                        })
                                if files:
                                    # 使用完整的消息内容作为key（更准确）
                                    msg_key = (db_msg.role, db_msg.content)
                                    msg_file_map[msg_key] = files
                        except json.JSONDecodeError:
                            pass
            finally:
                db.close()
        else:
            msg_file_map = {}
        
        # 转换消息格式
        result = []
        for msg in messages:
            msg_dict = {}
            if isinstance(msg, HumanMessage):
                msg_dict = {
                    'role': 'user',
                    'content': msg.content
                }
            elif isinstance(msg, AIMessage):
                msg_dict = {
                    'role': 'assistant',
                    'content': msg.content
                }
            elif isinstance(msg, SystemMessage):
                msg_dict = {
                    'role': 'system',
                    'content': msg.content
                }
            
            # 添加文件信息
            if include_files and msg_dict.get('role') == 'user':
                msg_key = (msg_dict['role'], msg_dict['content'])
                if msg_key in msg_file_map:
                    msg_dict['files'] = msg_file_map[msg_key]
            
            if msg_dict:
                result.append(msg_dict)
        
        return result
    
    def save_context(self, user_input: str, ai_output: str, user_file_ids: List[int] = None):
        """
        保存对话上下文
        
        Args:
            user_input: 用户输入
            ai_output: AI输出
            user_file_ids: 用户消息关联的文件ID列表（方案2：通过消息元数据传递）
        
        注意：
            - 用户消息和AI消息会先保存到数据库
            - 然后调用 LangChain Memory 的 save_context 更新内存（add_message 只更新内存，不保存数据库）
        """
        from langchain_core.messages import HumanMessage, AIMessage
        
        # 1. 保存用户消息到数据库（带 file_ids）
        user_message = HumanMessage(
            content=user_input,
            additional_kwargs={'file_ids': user_file_ids} if user_file_ids else {}
        )
        self.message_history.save_message_to_database(user_message)
        
        # 2. 保存AI消息到数据库
        ai_message = AIMessage(content=ai_output)
        self.message_history.save_message_to_database(ai_message)
        
        # 3. 调用 LangChain Memory 的 save_context 更新内存
        # add_message 方法只更新内存，不保存数据库，所以不会重复保存
        self.memory.save_context(
            {'input': user_input},
            {'output': ai_output}
        )
    
    def clear(self):
        """清空内存（仅清空内存，不删除数据库记录）"""
        self.memory.clear()
    
    def enrich_with_file_context(
        self,
        history_messages: List[Dict]
    ) -> List[Dict]:
        """
        使用文件服务丰富历史消息
        
        Args:
            history_messages: 历史消息列表
            
        Returns:
            丰富后的历史消息列表
        """
        return self.file_service.enrich_history_messages_with_files(
            history_messages,
            self.user_id
        )
    
    def get_current_file_context(self, file_ids: List[int]) -> str:
        """获取当前消息的文件上下文"""
        return self.file_service.get_file_contexts_from_ids(file_ids, self.user_id)
    
    def build_messages_for_api(
        self,
        user_message: str,
        file_ids: List[int] = None,
        system_prompt: str = None
    ) -> List[Dict]:
        """
        构建发送给 API 的消息列表
        
        Args:
            user_message: 用户消息
            file_ids: 当前消息的文件ID列表
            system_prompt: 系统提示词
            
        Returns:
            消息列表，格式为 [{'role': '...', 'content': '...'}, ...]
        """
        # 获取历史消息（字典格式，包含文件信息）
        history_messages = self.get_history_messages_as_dict(include_files=True)
        
        # 丰富历史消息（添加文件上下文）
        enriched_history = self.enrich_with_file_context(history_messages)
        
        # 构建消息列表
        api_messages = []
        
        # 添加系统提示词
        if system_prompt:
            api_messages.append({
                'role': 'system',
                'content': system_prompt
            })
        
        # 添加历史消息
        for msg in enriched_history:
            # 跳过系统消息（已经在上面添加了）
            if msg.get('role') == 'system':
                continue
            api_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # 获取当前消息的文件上下文
        file_context = self.get_current_file_context(file_ids) if file_ids else ""
        
        # 构建用户消息
        user_content = file_context + user_message if file_context else user_message
        
        # 添加当前用户消息
        api_messages.append({
            'role': 'user',
            'content': user_content
        })
        
        return api_messages

