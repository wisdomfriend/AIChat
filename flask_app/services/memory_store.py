"""自定义 Memory Store - 基于 MySQL 数据库"""
import json
from typing import List
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from ..database import get_session
from ..models import ChatMessage, ChatSession


class MySQLChatMessageHistory(BaseChatMessageHistory):
    """基于 MySQL 的聊天消息历史存储"""
    
    def __init__(self, session_id: int, user_id: int):
        """
        初始化
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（用于权限验证）
        """
        self.session_id = session_id
        self.user_id = user_id
        self._messages: List[BaseMessage] = []
        self._loaded = False
    
    @property
    def messages(self) -> List[BaseMessage]:
        """获取消息列表（懒加载）"""
        if not self._loaded:
            self._load_messages()
        return self._messages
    
    def _load_messages(self):
        """从数据库加载消息"""
        db = get_session()
        try:
            # 验证会话权限
            session = db.query(ChatSession).filter(
                ChatSession.id == self.session_id,
                ChatSession.user_id == self.user_id
            ).first()
            
            if not session:
                self._messages = []
                self._loaded = True
                return
            
            # 加载消息
            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == self.session_id
            ).order_by(ChatMessage.created_at.asc()).all()
            
            self._messages = []
            for msg in messages:
                if msg.role == 'user':
                    self._messages.append(HumanMessage(content=msg.content))
                elif msg.role == 'assistant':
                    self._messages.append(AIMessage(content=msg.content))
                elif msg.role == 'system':
                    self._messages.append(SystemMessage(content=msg.content))
            
            self._loaded = True
        except Exception as e:
            print(f"Load messages error: {e}")
            self._messages = []
            self._loaded = True
        finally:
            db.close()
    
    def add_message(self, message: BaseMessage):
        """
        添加消息到内存（LangChain Memory 使用，不保存数据库）
        
        Args:
            message: 消息对象
        """
        self._messages.append(message)
    
    def save_message_to_database(self, message: BaseMessage):
        """
        保存消息到数据库（业务层使用）
        
        Args:
            message: 消息对象
        """
        db = get_session()
        try:
            # 确定角色
            if isinstance(message, HumanMessage):
                role = 'user'
            elif isinstance(message, AIMessage):
                role = 'assistant'
            elif isinstance(message, SystemMessage):
                role = 'system'
            else:
                role = 'user'  # 默认
            
            # 从消息的 additional_kwargs 中提取 file_ids
            file_ids = None
            if isinstance(message, HumanMessage):
                # 只有用户消息才可能有 file_ids
                if hasattr(message, 'additional_kwargs') and message.additional_kwargs:
                    file_ids = message.additional_kwargs.get('file_ids')

            # 将 file_ids 转换为 JSON 字符串
            file_ids_str = json.dumps(file_ids) if file_ids else None
            
            # 保存消息
            chat_message = ChatMessage(
                session_id=self.session_id,
                role=role,
                content=message.content,
                file_ids=file_ids_str  # 保存文件ID
            )
            db.add(chat_message)
            db.commit()
        except Exception as e:
            print(f"Save message to database error: {e}")
            db.rollback()
        finally:
            db.close()
    
    def add_user_message(self, message: str):
        """添加用户消息到内存（不保存数据库）"""
        self.add_message(HumanMessage(content=message))
    
    def add_ai_message(self, message: str):
        """添加AI消息到内存（不保存数据库）"""
        self.add_message(AIMessage(content=message))
    
    def clear(self):
        """清空消息历史（仅清空内存，不删除数据库记录）"""
        self._messages = []
        self._loaded = False

