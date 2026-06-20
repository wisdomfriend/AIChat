"""MySQL 聊天持久化 — 用户可见消息与 checkpoint bootstrap。"""
import json
from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage

from ..config import Config
from ..database import get_session
from ..models import ChatMessage, ConversationSummary
from .file_service import FileService
from .memory_store import MySQLChatMessageHistory


class ChatPersistenceService:
    """管理 MySQL 展示层消息；PG checkpointer 负责 Agent 运行时记忆。"""

    BOOTSTRAP_MAX_MESSAGES = 40  # 约 20 轮 user+assistant

    def __init__(self, session_id: int, user_id: int):
        self.session_id = session_id
        self.user_id = user_id
        self.config = Config()
        self.file_service = FileService()
        self.message_history = MySQLChatMessageHistory(session_id, user_id)

    def build_user_message(self, user_message: str, file_ids: List[int] = None, llm_provider: str = None) -> HumanMessage:
        """构建带文件上下文的用户消息。"""
        text_file_ids = []
        if file_ids:
            provider_config = self.config.LLM_PROVIDERS.get(llm_provider or self.config.LLM_DEFAULT_PROVIDER, {})
            supports_images = provider_config.get("supports_images", False)
            for file_id in file_ids:
                file_info = self.file_service.get_file(file_id, self.user_id)
                if not file_info:
                    continue
                if self.file_service.extractor.is_image(file_info.get("file_extension", "")):
                    if supports_images:
                        return self._build_multimodal_message(user_message, file_ids, llm_provider)
                else:
                    text_file_ids.append(file_id)

        file_context = self.file_service.get_file_contexts_from_ids(text_file_ids, self.user_id) if text_file_ids else ""
        content = f"{file_context}\n\n{user_message}" if file_context else user_message
        return HumanMessage(content=content)

    def _build_multimodal_message(self, user_message: str, file_ids: List[int], llm_provider: str) -> HumanMessage:
        """多模态用户消息（图片 + 文本）。"""
        import base64
        import os

        from ..models import UploadedFile

        content_parts = []
        file_context = self.file_service.get_file_contexts_from_ids(
            [fid for fid in file_ids if not self._is_image_id(fid)], self.user_id
        )
        text = f"{file_context}\n\n{user_message}" if file_context else user_message
        if text:
            content_parts.append({"type": "text", "text": text})

        db = get_session()
        try:
            for file_id in file_ids:
                if not self._is_image_id(file_id):
                    continue
                uploaded_file = db.query(UploadedFile).filter(
                    UploadedFile.id == file_id,
                    UploadedFile.user_id == self.user_id,
                ).first()
                if not uploaded_file or not os.path.exists(uploaded_file.file_path):
                    continue
                with open(uploaded_file.file_path, "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode("utf-8")
                mime_type = uploaded_file.file_type or "image/jpeg"
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                })
        finally:
            db.close()

        return HumanMessage(content=content_parts or user_message)

    def _is_image_id(self, file_id: int) -> bool:
        file_info = self.file_service.get_file(file_id, self.user_id)
        if not file_info:
            return False
        return self.file_service.extractor.is_image(file_info.get("file_extension", ""))

    def get_bootstrap_messages(self) -> List:
        """从 MySQL 加载最近消息，用于首次写入 PG checkpoint。"""
        db = get_session()
        try:
            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.session_id == self.session_id)
                .order_by(ChatMessage.created_at.asc())
                .all()
            )
            if len(rows) > self.BOOTSTRAP_MAX_MESSAGES:
                rows = rows[-self.BOOTSTRAP_MAX_MESSAGES :]

            messages = []
            for row in rows:
                if row.role == "user":
                    messages.append(HumanMessage(content=row.content))
                elif row.role == "assistant":
                    messages.append(AIMessage(content=row.content))
            return messages
        finally:
            db.close()

    def save_turn(
        self,
        user_input: str,
        assistant_output: str,
        user_file_ids: List[int] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """保存一轮 user/assistant 到 MySQL。"""
        db = get_session()
        try:
            user_msg = ChatMessage(
                session_id=self.session_id,
                role="user",
                content=user_input,
                file_ids=json.dumps(user_file_ids) if user_file_ids else None,
            )
            db.add(user_msg)

            assistant_msg = ChatMessage(
                session_id=self.session_id,
                role="assistant",
                content=assistant_output,
                metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
            )
            db.add(assistant_msg)
            db.commit()
        except Exception as e:
            print(f"Save turn error: {e}")
            db.rollback()
        finally:
            db.close()

    def save_summary(self, message_count: int, summary_content: str, token_count: int = 0) -> None:
        """同步摘要到 MySQL（供 UI 提示）。"""
        db = get_session()
        try:
            db.query(ConversationSummary).filter(
                ConversationSummary.session_id == self.session_id
            ).delete()
            db.add(
                ConversationSummary(
                    session_id=self.session_id,
                    message_count=message_count,
                    summary_content=summary_content,
                    token_count=token_count,
                )
            )
            db.commit()
        except Exception as e:
            print(f"Save summary error: {e}")
            db.rollback()
        finally:
            db.close()
