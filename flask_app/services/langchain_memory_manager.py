"""LangChain Memory 管理器 - 简化版，只用于上下文压缩"""
from typing import List, Dict, Optional, Tuple

from langchain_core.messages import HumanMessage, AIMessage
from .memory_store import MySQLChatMessageHistory
from .file_service import FileService
from ..config import Config


class LangChainMemoryManager:
    """LangChain Memory 管理器（简化版）
    
    只保留以下功能：
    1. 从数据库读取历史消息
    2. 保存对话上下文到数据库
    3. 上下文压缩（使用 predict_new_summary）
    """
    
    def __init__(
        self,
        session_id: int,
        user_id: int
    ):
        """
        初始化
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        self.session_id = session_id
        self.user_id = user_id
        
        # 配置对象
        self.config = Config()
        
        # 创建消息历史存储（用于保存到数据库）
        self.message_history = MySQLChatMessageHistory(session_id, user_id)
        
        # 文件服务（用于处理文件上下文）
        self.file_service = FileService()
    
    def get_history_messages_as_dict(self, include_files: bool = True) -> List[Dict]:
        """
        获取历史消息列表（字典格式，包含消息ID）
        
        Args:
            include_files: 是否包含文件信息
            
        Returns:
            消息列表，格式为 [{'id': 1, 'role': '...', 'content': '...'}, ...]
        """
        from ..database import get_session
        from ..models import ChatMessage
        import json
        from .file_service import FileService
        
        db = get_session()
        try:
            # 从数据库加载所有消息（包含ID）
            db_messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id
            ).order_by(ChatMessage.created_at.asc()).all()
            
            # 创建消息内容到文件信息的映射
            msg_file_map = {}
            if include_files:
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
                                    msg_key = (db_msg.role, db_msg.content)
                                    msg_file_map[msg_key] = files
                        except json.JSONDecodeError:
                            pass
            
            # 转换消息格式，包含ID
            result = []
            for db_msg in db_messages:
                msg_dict = {
                    'id': db_msg.id,  # 添加消息ID
                    'role': db_msg.role,
                    'content': db_msg.content
                }
                
                # 添加文件信息
                if include_files and msg_dict.get('role') == 'user':
                    msg_key = (msg_dict['role'], msg_dict['content'])
                    if msg_key in msg_file_map:
                        msg_dict['files'] = msg_file_map[msg_key]
                
                result.append(msg_dict)
            
            return result
        finally:
            db.close()
    
    def save_context(self, user_input: str, ai_output: str, user_file_ids: List[int] = None):
        """
        保存对话上下文到数据库
        
        Args:
            user_input: 用户输入
            ai_output: AI输出
            user_file_ids: 用户消息关联的文件ID列表
        """
        from langchain_core.messages import HumanMessage, AIMessage
        
        # 保存用户消息到数据库（带 file_ids）
        user_message = HumanMessage(
            content=user_input,
            additional_kwargs={'file_ids': user_file_ids} if user_file_ids else {}
        )
        self.message_history.save_message_to_database(user_message)
        
        # 保存AI消息到数据库
        ai_message = AIMessage(content=ai_output)
        self.message_history.save_message_to_database(ai_message)
    
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
    
    def get_latest_summary(self) -> Optional[Dict]:
        """
        获取会话的最新摘要（只有最新摘要生效）
        
        Returns:
            摘要字典，格式为 {'id': 1, 'message_count': 50, 'summary_content': '...', 'created_at': '...'}
            如果没有摘要，返回 None
        """
        from ..database import get_session
        from ..models import ConversationSummary
        
        db = get_session()
        try:
            summary = db.query(ConversationSummary).filter(
                ConversationSummary.session_id == self.session_id
            ).order_by(ConversationSummary.created_at.desc()).first()
            
            if summary:
                return {
                    'id': summary.id,
                    'message_count': summary.message_count,
                    'summary_content': summary.summary_content,
                    'token_count': summary.token_count,
                    'created_at': summary.created_at
                }
            return None
        finally:
            db.close()
    
    def apply_summary_to_messages(self, messages: List[Dict]) -> Tuple[List[Dict], Optional[str]]:
        """
        应用最新摘要到消息列表
        
        逻辑：
        1. 检查是否有最新摘要
        2. 如果有，删除前 message_count 轮对应的消息
        3. 返回剩余消息和摘要内容
        
        Args:
            messages: 消息列表（包含id字段）
            
        Returns:
            (剩余消息列表, 摘要内容) 或 (消息列表, None)
        """
        summary = self.get_latest_summary()
        if not summary:
            return messages, None
        
        message_count = summary['message_count']  # 覆盖的轮数
        
        # 计算需要删除的消息数量（每轮2条消息：user + assistant）
        messages_to_remove = message_count * 2
        
        if len(messages) <= messages_to_remove:
            # 如果消息总数少于需要删除的数量，只保留摘要
            return [], summary['summary_content']
        
        # 删除前 messages_to_remove 条消息
        remaining_messages = messages[messages_to_remove:]
        
        # 返回剩余消息和摘要内容（摘要不作为消息返回）
        return remaining_messages, summary['summary_content']
    
    def count_message_rounds(self, messages: List[Dict]) -> int:
        """
        计算消息的轮数（每轮 = 1 user + 1 assistant）
        
        Args:
            messages: 消息列表（排除system消息）
            
        Returns:
            轮数
        """
        # 过滤掉system消息
        non_system_messages = [msg for msg in messages if msg.get('role') != 'system']
        # 每轮2条消息
        return len(non_system_messages) // 2
    
    def build_messages_for_api(
        self,
        user_message: str,
        file_ids: List[int] = None,
        system_prompt: str = None,
        llm_provider: str = None
    ) -> List[Dict]:
        """
        构建发送给 API 的消息列表（支持摘要应用和自动压缩）
        
        Args:
            user_message: 用户消息
            file_ids: 当前消息的文件ID列表
            system_prompt: 系统提示词
            llm_provider: 模型提供商ID（用于压缩）
            
        Returns:
            消息列表，格式为 [{'role': '...', 'content': '...'}, ...]
        """
        # 获取历史消息（字典格式，包含文件信息和ID）
        history_messages = self.get_history_messages_as_dict(include_files=True)
        
        # 丰富历史消息（添加文件上下文）
        enriched_history = self.enrich_with_file_context(history_messages)
        
        # 应用摘要（如果有）
        remaining_messages, summary_content = self.apply_summary_to_messages(enriched_history)
        
        # 构建消息列表（先不包含系统提示词）
        api_messages = []
        
        # 添加历史消息（已应用摘要后的剩余消息）
        for msg in remaining_messages:
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
        
        # 检查是否需要压缩
        if llm_provider and self.config.LANGCHAIN_COMPRESSION_ENABLED:
            from .llm_service import LLMService
            llm_service = LLMService(self.config)
            
            # 临时添加系统提示词用于计算token（不包含摘要，因为压缩可能会生成新摘要）
            temp_messages = []
            if system_prompt:
                temp_messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            temp_messages.extend(api_messages)
            
            # 计算当前token数
            current_tokens = llm_service.count_tokens(temp_messages, llm_provider)
            max_context = llm_service.get_max_context_length(llm_provider)
            threshold = max_context * self.config.LANGCHAIN_COMPRESSION_THRESHOLD
            
            # 如果超过阈值，执行压缩
            if current_tokens > threshold:
                api_messages = self._compress_messages(
                    api_messages,
                    enriched_history,
                    llm_provider
                )
                # 压缩后重新获取最新摘要（压缩可能生成了新摘要）
                summary_content = self.get_latest_summary()
                if summary_content:
                    summary_content = summary_content['summary_content']
        
        # 压缩逻辑处理完成后，统一构建系统提示词
        system_content_parts = []
        if summary_content:
            system_content_parts.append(f"[历史摘要]\n{summary_content}")
        if system_prompt:
            system_content_parts.append(system_prompt)
        
        # 构建最终消息列表（系统提示词在最前面）
        final_messages = []
        
        # 添加系统提示词（只有一个system消息）
        if system_content_parts:
            final_messages.append({
                'role': 'system',
                'content': '\n\n'.join(system_content_parts)
            })
        
        # 添加历史消息和当前用户消息
        final_messages.extend(api_messages)
        
        return final_messages
    
    def _compress_messages(
        self,
        current_messages: List[Dict],
        enriched_history_messages: List[Dict],
        llm_provider: str
    ) -> List[Dict]:
        """
        压缩消息（超过80%阈值时触发）
        
        逻辑：
        1. 保留最近10轮（20条消息）
        2. 检查是否有旧摘要
        3. 如果有旧摘要：旧摘要 + 新消息一起压缩
        4. 如果没有旧摘要：直接压缩需要压缩的消息
        5. 保存新摘要
        
        Args:
            current_messages: 当前构建的消息列表（不包含系统提示词，只包含历史消息和当前用户消息，已包含文件上下文）
            enriched_history_messages: 所有历史消息（已包含文件上下文，用于计算轮数和提取需要压缩的消息内容）
            llm_provider: 模型提供商ID
            
        Returns:
            压缩后的消息列表（不包含系统提示词，只包含历史消息和当前用户消息）
        """
        from .llm_service import LLMService
        from ..database import get_session
        from ..models import ConversationSummary
        
        llm_service = LLMService(self.config)
        keep_rounds = self.config.LANGCHAIN_COMPRESSION_KEEP_ROUNDS  # 保留10轮
        
        # 计算总轮数（排除system消息和当前消息）
        non_system_messages = enriched_history_messages
        total_rounds = len(non_system_messages) // 2
        
        # 需要压缩的轮数
        compress_rounds = total_rounds - keep_rounds
        if compress_rounds <= 0:
            # 不需要压缩
            return current_messages
        
        # 获取旧摘要
        old_summary = self.get_latest_summary()
        
        # 计算需要压缩的消息范围
        compress_message_count = compress_rounds * 2  # 每轮2条消息
        messages_to_compress = non_system_messages[:compress_message_count]
        
        # 使用 LangChain 的 ConversationSummaryMemory 的总结方法
        llm = llm_service.get_llm(llm_provider)
        from langchain_core.messages import HumanMessage, AIMessage
        
        try:
            # 创建临时的 ConversationSummaryMemory 实例来使用其总结方法
            from langchain.memory import ConversationSummaryMemory
            from langchain_core.chat_history import InMemoryChatMessageHistory
            
            # 确定需要总结的消息
            if old_summary:
                # 有旧摘要：只总结旧摘要之后的新消息
                old_summary_rounds = old_summary['message_count']
                new_messages_start = old_summary_rounds * 2
                messages_to_summarize_raw = non_system_messages[new_messages_start:compress_message_count]
                existing_summary = old_summary['summary_content']
            else:
                # 没有旧摘要：总结所有需要压缩的消息
                messages_to_summarize_raw = messages_to_compress
                existing_summary = ""
            
            # 将需要压缩的消息转换为 LangChain 消息格式
            messages_to_summarize = []
            for msg in messages_to_summarize_raw:
                if msg['role'] == 'user':
                    messages_to_summarize.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages_to_summarize.append(AIMessage(content=msg['content']))
            
            # 创建临时 memory 实例来使用其总结方法
            temp_chat_history = InMemoryChatMessageHistory()
            temp_memory = ConversationSummaryMemory(
                llm=llm,
                chat_memory=temp_chat_history,
                return_messages=True
            )
            
            # 使用 LangChain 的 predict_new_summary 方法生成摘要
            # 这个方法会自动处理现有摘要和新消息的合并，使用 LangChain 的标准提示词模板
            summary_content = temp_memory.predict_new_summary(
                messages=messages_to_summarize,
                existing_summary=existing_summary
            )
            
        except Exception as e:
            print(f"Compress messages error (using LangChain): {e}")
            # 压缩失败，返回原消息列表
            return current_messages
        
        # 保存新摘要
        db = get_session()
        try:
            # 删除旧摘要（只保留最新摘要）
            db.query(ConversationSummary).filter(
                ConversationSummary.session_id == self.session_id
            ).delete()
            
            # 保存新摘要
            token_count = llm_service.count_tokens(
                [{'role': 'system', 'content': summary_content}],
                llm_provider
            )
            
            new_summary = ConversationSummary(
                session_id=self.session_id,
                message_count=compress_rounds,  # 覆盖的轮数
                summary_content=summary_content,
                token_count=token_count
            )
            db.add(new_summary)
            db.commit()
        except Exception as e:
            print(f"Save summary error: {e}")
            db.rollback()
        finally:
            db.close()
        
        # 构建压缩后的消息列表（不包含系统提示词）
        result = []
        
        # 从 current_messages 中提取历史消息和当前用户消息
        # current_messages 已经包含了文件上下文，并且已经应用了摘要
        # 结构：历史消息 + 当前用户消息（最后一条）
        if not current_messages:
            return result
        
        # 分离历史消息和当前用户消息
        # 最后一条消息是当前用户消息，其他都是历史消息
        history_in_current = current_messages[:-1]  # 除最后一条外的所有消息
        current_user_msg = current_messages[-1]  # 最后一条消息
        
        # 添加保留的最近消息（从 current_messages 中的历史消息部分获取）
        keep_message_count = keep_rounds * 2
        keep_messages = history_in_current[-keep_message_count:] if len(history_in_current) > keep_message_count else history_in_current
        
        for msg in keep_messages:
            result.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        # 添加当前用户消息
        result.append({
            'role': current_user_msg['role'],
            'content': current_user_msg['content']
        })
        
        return result

