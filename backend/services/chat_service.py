"""聊天 Service — 会话管理与 SSE 流式响应（统一 create_agent 模式）。"""
import json
import traceback

from sqlalchemy import func

from ..config import Config
from ..db import get_session
from ..db import ChatMessage, ChatSession, TokenUsage
from .chat_persistence import ChatPersistenceService
from .checkpointer_service import delete_thread
from .file_service import FileService


class ChatService:
    """聊天核心业务：会话 CRUD、Agent 流式生成。"""

    def __init__(self, agent_service, llm_service, config=None):
        self.config = config or Config()
        self.llm_service = llm_service
        self.agent_service = agent_service

    def save_token_usage(self, user_id: object, usage_data: object, model_name: object) -> object:
        db = get_session()
        try:
            token_usage = TokenUsage(
                user_id=user_id,
                prompt_tokens=usage_data.get('prompt_tokens', 0),
                completion_tokens=usage_data.get('completion_tokens', 0),
                total_tokens=usage_data.get('total_tokens', 0),
                model=model_name
            )
            db.add(token_usage)
            db.commit()
        except Exception as e:
            print(f"Save token usage error: {e}")
            db.rollback()
        finally:
            db.close()

    def create_session(self, user_id, title=None, llm_provider=None):
        db = get_session()
        try:
            if not title:
                title = "新对话"
            provider_id = llm_provider or self.config.LLM_DEFAULT_PROVIDER
            session = ChatSession(user_id=user_id, title=title)
            if hasattr(session, 'llm_provider'):
                session.llm_provider = provider_id
            db.add(session)
            db.commit()
            db.refresh(session)
            return session.id
        except Exception as e:
            print(f"Create session error: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def get_sessions(self, user_id, limit=200):
        db = get_session()
        try:
            try:
                sessions = db.query(ChatSession).filter(
                    ChatSession.user_id == user_id
                ).order_by(
                    ChatSession.is_pinned.desc(),
                    ChatSession.updated_at.desc(),
                ).limit(limit).all()
            except Exception as order_error:
                print(f"Get sessions fallback order: {order_error}")
                db.rollback()
                sessions = db.query(ChatSession).filter(
                    ChatSession.user_id == user_id
                ).order_by(
                    ChatSession.updated_at.desc()
                ).limit(limit).all()

            session_ids = [s.id for s in sessions]
            message_count_map = {}
            if session_ids:
                message_counts = db.query(
                    ChatMessage.session_id,
                    func.count(ChatMessage.id)
                ).filter(
                    ChatMessage.session_id.in_(session_ids)
                ).group_by(
                    ChatMessage.session_id
                ).all()
                message_count_map = {sid: count for sid, count in message_counts}

            return [{
                'id': s.id,
                'title': s.title,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None,
                'message_count': message_count_map.get(s.id, 0),
                'is_pinned': bool(getattr(s, 'is_pinned', False)),
            } for s in sessions]
        except Exception as e:
            print(f"Get sessions error: {e}")
            return []
        finally:
            db.close()

    def get_session_messages(self, session_id, user_id, include_files=False):
        db = get_session()
        try:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            if not session:
                return None

            messages = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.created_at.asc()).all()

            result = []
            for m in messages:
                msg_data = {'role': m.role, 'content': m.content}
                if m.metadata_json:
                    try:
                        msg_data['metadata'] = json.loads(m.metadata_json)
                    except json.JSONDecodeError:
                        pass

                if m.file_ids and include_files:
                    try:
                        file_ids = json.loads(m.file_ids)
                        if file_ids:
                            file_service = FileService()
                            files = []
                            for fid in file_ids:
                                file_info = file_service.get_file(fid, user_id)
                                if file_info:
                                    files.append({
                                        'id': file_info['id'],
                                        'filename': file_info['original_filename'],
                                        'file_size': file_info['file_size'],
                                        'file_extension': file_info['file_extension']
                                    })
                            msg_data['files'] = files
                    except json.JSONDecodeError:
                        pass
                result.append(msg_data)
            return result
        except Exception as e:
            print(f"Get session messages error: {e}")
            return None
        finally:
            db.close()

    def update_session_title(self, session_id, user_id, title):
        db = get_session()
        try:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            if session:
                session.title = title
                db.commit()
                return True
            return False
        except Exception as e:
            print(f"Update session title error: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def set_session_pinned(self, session_id, user_id, pinned=True):
        db = get_session()
        try:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            if not session:
                return False
            session.is_pinned = bool(pinned)
            db.commit()
            return True
        except Exception as e:
            print(f"Set session pinned error: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def delete_session(self, session_id, user_id):
        db = get_session()
        try:
            session = db.query(ChatSession).filter(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            ).first()
            if not session:
                return False
            db.delete(session)
            db.commit()
            delete_thread(session_id)
            return True
        except Exception as e:
            print(f"Delete session error: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def generate_title_from_message(self, message):
        if not message:
            return "新对话"
        title = message.strip()[:30]
        if len(message) > 30:
            title += "..."
        return title

    def process_chat_stream_with_session(self, user_id, session_id, message, file_ids=None, llm_provider=None):
        """处理带会话的 Agent 流式聊天。

        这是一个「生成器函数」，通过 yield 逐块输出 SSE（Server-Sent Events）数据，
        供 Flask 路由以 text/event-stream 形式推送给前端。

        整体流程：会话准备 → 权限校验 → 确定 LLM → 构建消息 → 委托 Agent 流式执行。
        """
        try:
            # ── 会话准备（新对话时自动建会话）──
            if not session_id:
                # 前端首次发消息时 session_id 为空，用消息前 30 字作为标题
                title = self.generate_title_from_message(message)
                session_id = self.create_session(user_id, title, llm_provider)
                if not session_id:
                    yield f"data: {json.dumps({'type': 'error', 'message': '创建会话失败'})}\n\n"
                    return
                # 通知前端新会话 ID，便于后续请求带上 session_id
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

            # ── 校验会话归属 + 确定 LLM 提供商 ──
            db = get_session()
            try:
                # 必须同时匹配 session_id 与 user_id，防止越权访问他人会话
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                if not session:
                    yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在或无权限'})}\n\n"
                    return

                if llm_provider:
                    # 请求显式指定模型时，更新会话记录并优先使用
                    provider_id = llm_provider
                    if hasattr(session, 'llm_provider'):
                        session.llm_provider = provider_id
                        db.commit()
                else:
                    # 未指定则沿用会话已保存的 provider，再回退到全局默认
                    provider_id = getattr(session, 'llm_provider', None) or self.config.LLM_DEFAULT_PROVIDER
            finally:
                db.close()

            # ── 构建 Agent 输入 ──
            persistence = ChatPersistenceService(session_id=session_id, user_id=user_id)
            # 将用户文本 + 附件内容拼成 LangChain HumanMessage（支持多模态图片）
            user_message = persistence.build_user_message(message, file_ids, provider_id)
            # 从 MySQL 拉最近历史，用于 PG checkpoint 首次为空时的 bootstrap
            seed_messages = persistence.get_bootstrap_messages()

            # ── 阶段 4：流式执行 Agent，并透传所有 SSE 事件 ──
            yield from self._process_agent_stream(
                user_id=user_id,
                session_id=session_id,
                provider_id=provider_id,
                persistence=persistence,
                user_message=user_message,
                original_message=message,  # 存库用原始文本，不含文件注入前缀
                file_ids=file_ids,
                seed_messages=seed_messages,
            )
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Process chat stream error: {e}")
            print(f"详细错误信息:\n{error_traceback}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时出错: {str(e)}'})}\n\n"

    def _process_agent_stream(
        self,
        user_id,
        session_id,
        provider_id,
        persistence,
        user_message,
        original_message,
        file_ids,
        seed_messages,
    ):
        try:
            assistant_content = ''
            usage = None
            tool_calls = []

            for chunk in self.agent_service.run_agent_stream(
                provider_id=provider_id,
                session_id=session_id,
                user_message=user_message,
                seed_messages=seed_messages,
            ):
                yield chunk

                if chunk.startswith('data: '):
                    try:
                        data = json.loads(chunk[6:].strip())
                        if data.get('type') == 'content':
                            assistant_content += data.get('content', '')
                        elif data.get('type') == 'usage':
                            usage = data.get('usage')
                        elif data.get('type') == 'done':
                            tool_calls = data.get('tool_calls', [])
                    except (json.JSONDecodeError, KeyError):
                        pass

            if assistant_content:
                metadata = {'tool_calls': tool_calls} if tool_calls else None
                persistence.save_turn(
                    original_message,
                    assistant_content,
                    user_file_ids=file_ids if file_ids else None,
                    metadata=metadata,
                )

            if usage:
                provider_config = self.llm_service.get_provider_config(provider_id)
                model_name = provider_config.get('model_name', provider_id)
                self.save_token_usage(user_id, usage, model_name)

            db = get_session()
            try:
                msg_count = db.query(ChatMessage).filter(
                    ChatMessage.session_id == session_id
                ).count()
            finally:
                db.close()

            if msg_count == 2:
                title = self.generate_title_from_message(original_message)
                self.update_session_title(session_id, user_id, title)
                yield f"data: {json.dumps({'type': 'session_title', 'title': title})}\n\n"

        except Exception as e:
            print(f"Process agent stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Agent 处理错误: {str(e)}'})}\n\n"
