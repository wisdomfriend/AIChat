"""聊天 Service — 会话管理与 SSE 流式响应。

职责总览（按聊天流程）：
1) 会话
   - `create_session()` / `get_sessions()` / `get_session_messages()`
   - `get_latest_session_id()` / `update_session_title()`
2) 消息
   - `save_message()` / `process_chat_stream_with_session()`
3) 用量
   - `save_token_usage()`  记录 Token 消耗
"""
import asyncio
import json
import traceback
from datetime import datetime

from sqlalchemy import func

from ..config import Config
from ..database import get_session, ensure_schema
from ..models import ApiKey, ChatMessage, ChatSession, TokenUsage
from .agent_service import AgentService
from .baidu_search_service import BaiduSearchService
from .file_service import FileService
from .langchain_memory_manager import LangChainMemoryManager
from .llm_service import LLMService


class ChatService:
    """聊天核心业务：会话 CRUD、多模式流式生成（normal / web_search / react / plan_execute）。"""
    
    def __init__(self):
        self.config = Config()
        self.llm_service = LLMService(self.config)
        self.search_service = BaiduSearchService(self.config)
        self.agent_service = AgentService(self.config)
    
    def save_token_usage(self, user_id, usage_data, model_name):
        """将 LLM 调用的 Token 用量写入 `token_usage` 表。

        用法:
        - 调用方: 流式聊天结束后
        - 参数: `user_id`、`usage_data`（prompt/completion/total tokens）、`model_name`
        """
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
        """创建新的聊天会话。

        用法:
        - 调用方: `process_chat_stream_with_session()`（session_id 为空时）
        - 参数: `user_id`、`title`（默认「新对话」）、`llm_provider`
        - 返回值: 新会话 ID
        """
        db = get_session()
        try:
            if not title:
                title = "新对话"
            
            # 确定使用的模型提供商
            provider_id = llm_provider or self.config.LLM_DEFAULT_PROVIDER
            
            session = ChatSession(
                user_id=user_id,
                title=title
            )
            # 如果表中有 llm_provider 字段，设置它
            if hasattr(ChatSession, 'llm_provider'):
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
    
    def save_message(self, session_id, role, content, file_ids=None):
        """保存单条聊天消息到 `chat_messages` 表。

        用法:
        - 调用方: 流式聊天过程中
        - 参数: `session_id`、`role`（user/assistant）、`content`、`file_ids`
        """
        db = get_session()
        try:
            # 将 file_ids 转换为 JSON 字符串
            file_ids_str = json.dumps(file_ids) if file_ids else None
            
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                file_ids=file_ids_str
            )
            db.add(message)
            db.commit()
        except Exception as e:
            print(f"Save message error: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_sessions(self, user_id, limit=50):
        """获取用户的会话列表（含消息数）。

        用法:
        - 调用方: `GET /api/sessions`
        - 参数: `user_id`、`limit`（默认 50）
        - 返回值: `[{ id, title, created_at, updated_at, message_count }, ...]`
        """
        ensure_schema()
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

    def get_latest_session_id(self, user_id, prefer_non_empty=True):
        """获取用户最近使用的会话 ID。

        用法:
        - 调用方: `routes/chat.chat` 初始化页面
        - 参数: `prefer_non_empty` — True 时优先返回有消息的会话
        - 返回值: 会话 ID 或 None
        """
        db = get_session()
        try:
            if prefer_non_empty:
                latest_non_empty = db.query(ChatSession.id).join(
                    ChatMessage,
                    ChatMessage.session_id == ChatSession.id
                ).filter(
                    ChatSession.user_id == user_id
                ).group_by(
                    ChatSession.id
                ).order_by(
                    ChatSession.updated_at.desc()
                ).first()

                if latest_non_empty:
                    return latest_non_empty[0]

            latest_session = db.query(ChatSession.id).filter(
                ChatSession.user_id == user_id
            ).order_by(
                ChatSession.updated_at.desc()
            ).first()

            return latest_session[0] if latest_session else None
        except Exception as e:
            print(f"Get latest session id error: {e}")
            return None
        finally:
            db.close()
    
    def get_session_messages(self, session_id, user_id, include_files=False):
        """获取指定会话的全部消息。

        用法:
        - 调用方: `GET /api/sessions/<id>/messages`
        - 参数: `session_id`、`user_id`（权限校验）、`include_files`
        - 返回值: 消息列表；无权限时返回 None
        """
        db = get_session()
        try:
            # 验证会话属于该用户
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
                msg_data = {
                    'role': m.role,
                    'content': m.content
                }
                
                # 解析文件ID并获取文件信息
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
        """更新会话标题。

        用法:
        - 参数: `session_id`、`user_id`（权限校验）、`title`
        - 返回值: True 成功，False 会话不存在
        """
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
        """固定或解除固定会话。"""
        ensure_schema()
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
        """删除会话及其关联消息（依赖数据库级联）。"""
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
            return True
        except Exception as e:
            print(f"Delete session error: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def generate_title_from_message(self, message):
        """从首条用户消息截取会话标题（最多 30 字符）。

        用法:
        - 调用方: 创建新会话时
        - 返回值: 标题字符串，空消息时返回「新对话」
        """
        if not message:
            return "新对话"
        
        # 简单处理：取前30个字符作为主题
        title = message.strip()[:30]
        if len(message) > 30:
            title += "..."
        return title
    
    def process_chat_stream_with_session(self, user_id, session_id, message, file_ids=None, llm_provider=None, agent_mode='normal'):
        """处理带会话的流式聊天，yield SSE 事件。

        用法:
        - 调用方: `POST /api/chat`
        - 参数: `user_id`、`session_id`（None 则新建）、`message`、`file_ids`、`llm_provider`
        - 参数: `agent_mode` — `normal` / `web_search` / `react` / `plan_execute`
        - 返回值: 生成器，yield `data: {"type": "chunk"|"session_id"|"end"|"error", ...}\n\n`
        """
        try:
            # 如果session_id为None，创建新会话
            if not session_id:
                title = self.generate_title_from_message(message)
                session_id = self.create_session(user_id, title, llm_provider)
                if not session_id:
                    yield f"data: {json.dumps({'type': 'error', 'message': '创建会话失败'})}\n\n"
                    return
                # 发送会话ID给前端
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            
            # 验证会话权限并确定使用的模型
            db = get_session()
            try:
                session = db.query(ChatSession).filter(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                ).first()
                if not session:
                    yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在或无权限'})}\n\n"
                    return
                
                # 确定使用的模型提供商
                if llm_provider:
                    # 请求中指定了模型，使用指定的并更新会话
                    provider_id = llm_provider
                    if hasattr(session, 'llm_provider'):
                        session.llm_provider = provider_id
                        db.commit()
                else:
                    # 使用会话保存的模型，如果会话没有则使用默认
                    provider_id = getattr(session, 'llm_provider', None) or self.config.LLM_DEFAULT_PROVIDER
            finally:
                db.close()
            
            # 创建 LangChain Memory Manager
            memory_manager = LangChainMemoryManager(
                session_id=session_id,
                user_id=user_id
            )
            
            # 根据 agent_mode 选择处理方式
            original_message = message
            
            # Agent 模式：react 或 plan_execute
            if agent_mode in ['react', 'plan_execute']:
                yield from self._process_agent_chat(
                    user_id, session_id, message, file_ids, provider_id, 
                    memory_manager, agent_mode
                )
                return
            
            # 联网搜索模式
            use_web_search = (agent_mode == 'web_search')
            if use_web_search:
                try:
                    # 发送搜索开始提示
                    yield f"data: {json.dumps({'type': 'search_start', 'message': '正在搜索相关信息...'})}\n\n"
                    
                    # 执行搜索
                    search_results = self.search_service.search(
                        query=message,
                        num_results=self.config.BAIDU_SEARCH_NUM_RESULTS
                    )
                    
                    # 将搜索结果拼接到用户消息前
                    message = f"{search_results}\n\n用户问题：{message}"
                    
                    # 发送搜索完成提示
                    yield f"data: {json.dumps({'type': 'search_complete', 'message': '搜索完成'})}\n\n"
                except Exception as e:
                    print(f"Web search error: {e}")
                    # 搜索失败不影响正常流程，继续使用原始消息
                    yield f"data: {json.dumps({'type': 'search_error', 'message': f'搜索失败: {str(e)}'})}\n\n"
            
            # 构建系统提示词
            system_prompt = "你是一个友好、专业且乐于助人的AI助手。你的目标是提供准确、有用和清晰的信息，帮助用户解决问题。请用简洁明了的语言回答，如果遇到不确定的问题，请诚实说明。"
            if file_ids:
                system_prompt += "\n\n用户可能会上传文件，当用户上传文件时，请仔细阅读文件内容并基于文件内容回答问题。"
            if use_web_search:
                system_prompt += "\n\n用户启用了联网搜索功能，搜索结果已包含在用户消息中。请基于搜索结果和你的知识来回答问题，优先使用搜索结果中的最新信息。"
            
            # 使用 LangChain Memory Manager 构建消息列表（支持摘要和压缩）
            api_messages = memory_manager.build_messages_for_api(
                user_message=message,
                file_ids=file_ids,
                system_prompt=system_prompt,
                llm_provider=provider_id
            )
            
            # 调用流式API（使用 LLMService）
            # 注意：保存消息时使用原始消息，而不是包含搜索结果的消息
            yield from self._process_normal_chat(
                api_messages, provider_id, memory_manager, original_message, file_ids, user_id, session_id
            )
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Process chat stream with session outer error: {e}")
            print(f"详细错误信息:\n{error_traceback}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时出错: {str(e)}'})}\n\n"
    
    def _process_normal_chat(self, api_messages, provider_id, memory_manager, message, file_ids, user_id, session_id):
        """处理普通 LLM 聊天（非 Agent 模式）"""
        try:
            usage = None
            assistant_content = ''
            
            # 运行异步流式生成器
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async_gen = self.llm_service.stream_chat(api_messages, provider_id)
                
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                        
                        # 解析 chunk 提取内容
                        if chunk.startswith('data: '):
                            try:
                                data_str = chunk[6:].strip()
                                if data_str:
                                    data = json.loads(data_str)
                                    if data.get('type') == 'content':
                                        assistant_content += data.get('content', '')
                                    elif data.get('type') == 'usage':
                                        usage = data.get('usage')
                            except (json.JSONDecodeError, KeyError):
                                pass
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
            
            # 保存AI回复和用户消息
            if assistant_content:
                # 使用 LangChain Memory Manager 保存对话上下文
                memory_manager.save_context(message, assistant_content, user_file_ids=file_ids if file_ids else None)
            
            # 保存token使用记录
            if usage:
                # 获取模型名称
                provider_config = self.llm_service.get_provider_config(provider_id)
                model_name = provider_config.get('model_name', provider_id)
                self.save_token_usage(user_id, usage, model_name)
            
            # 如果是新会话且只有一条用户消息，更新主题
            history_messages = memory_manager.get_history_messages_as_dict()
            if len(history_messages) <= 2:  # 只有当前这一轮对话（user + assistant）
                title = self.generate_title_from_message(message)
                self.update_session_title(session_id, user_id, title)
                yield f"data: {json.dumps({'type': 'session_title', 'title': title})}\n\n"
                
        except Exception as e:
            print(f"Process normal chat error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时出错: {str(e)}'})}\n\n"
    
    def _process_agent_chat(self, user_id, session_id, message, file_ids, provider_id, memory_manager, agent_mode):
        """处理 Agent 模式的聊天（ReAct 或 Plan-and-Execute）
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            message: 用户消息
            file_ids: 文件ID列表
            provider_id: 模型提供商ID
            memory_manager: LangChain Memory Manager
            agent_mode: Agent 模式（'react' 或 'plan_execute'）
            
        Yields:
            SSE格式的数据流
        """
        try:
            # 获取历史消息（用于 Agent 的上下文）
            history_messages = memory_manager.get_history_messages_as_dict(include_files=False)
            
            # 如果有文件，将文件内容添加到消息中
            if file_ids:
                file_service = FileService()
                file_context = file_service.get_file_contexts_from_ids(file_ids, user_id)
                if file_context:
                    message = f"{file_context}\n\n用户问题：{message}"
            
            # 根据 Agent 模式选择执行方法
            if agent_mode == 'react':
                agent_gen = self.agent_service.run_react_agent_stream(
                    provider_id=provider_id,
                    user_input=message,
                    chat_history=history_messages
                )
            elif agent_mode == 'plan_execute':
                agent_gen = self.agent_service.run_plan_execute_agent_stream(
                    provider_id=provider_id,
                    user_input=message,
                    chat_history=history_messages
                )
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': f'不支持的 Agent 模式: {agent_mode}'})}\n\n"
                return
            
            # 运行异步生成器
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                assistant_content = ''
                usage = None
                
                while True:
                    try:
                        chunk = loop.run_until_complete(agent_gen.__anext__())
                        yield chunk
                        
                        # 解析 chunk 提取内容
                        if chunk.startswith('data: '):
                            try:
                                data_str = chunk[6:].strip()
                                if data_str:
                                    data = json.loads(data_str)
                                    if data.get('type') == 'content':
                                        assistant_content += data.get('content', '')
                                    elif data.get('type') == 'usage':
                                        usage = data.get('usage')
                            except (json.JSONDecodeError, KeyError):
                                pass
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
            
            # 保存对话上下文
            if assistant_content:
                memory_manager.save_context(message, assistant_content, user_file_ids=file_ids if file_ids else None)
            
            # 保存 token 使用记录（Agent 模式可能没有 usage，这里尝试保存）
            if usage:
                provider_config = self.llm_service.get_provider_config(provider_id)
                model_name = provider_config.get('model_name', provider_id)
                self.save_token_usage(user_id, usage, model_name)
            
            # 更新会话主题（如果是新会话）
            history_messages = memory_manager.get_history_messages_as_dict()
            if len(history_messages) <= 2:
                title = self.generate_title_from_message(message)
                self.update_session_title(session_id, user_id, title)
                yield f"data: {json.dumps({'type': 'session_title', 'title': title})}\n\n"
                
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Process agent chat error: {e}")
            print(f"详细错误信息:\n{error_traceback}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Agent 处理错误: {str(e)}'})}\n\n"
    
