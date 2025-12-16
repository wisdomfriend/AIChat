"""聊天服务"""
import json
import requests
from datetime import datetime
from ..database import get_session
from ..models import ApiKey, TokenUsage, ChatSession, ChatMessage
from ..config import Config


class ChatService:
    """聊天相关业务逻辑"""
    
    def __init__(self):
        self.config = Config()
        self.api_url = self.config.DEEPSEEK_API_URL
    
    def get_active_api_key(self):
        """获取当前活跃的API key"""
        db = get_session()
        try:
            api_key_obj = db.query(ApiKey).filter(ApiKey.is_active == True).first()
            return api_key_obj.api_key if api_key_obj else None
        finally:
            db.close()
    
    def call_deepseek_api(self, messages, api_key, stream=False):
        """调用DeepSeek API
        
        Args:
            messages: 消息列表，格式为 [{'role': 'user', 'content': '...'}, ...]
            api_key: API密钥
            stream: 是否使用流式响应
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': 'deepseek-chat',
            'messages': messages,
            'stream': stream
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=30, stream=stream)
        return response
    
    def save_token_usage(self, user_id, usage_data):
        """保存token使用记录"""
        db = get_session()
        try:
            token_usage = TokenUsage(
                user_id=user_id,
                prompt_tokens=usage_data.get('prompt_tokens', 0),
                completion_tokens=usage_data.get('completion_tokens', 0),
                total_tokens=usage_data.get('total_tokens', 0),
                model='deepseek-chat'
            )
            db.add(token_usage)
            db.commit()
        except Exception as e:
            print(f"Save token usage error: {e}")
            db.rollback()
        finally:
            db.close()
    
    def process_chat(self, user_id, message):
        """处理聊天请求"""
        # 获取API key
        api_key = self.get_active_api_key()
        if not api_key:
            return {
                'success': False,
                'error': '未配置API key'
            }
        
        # 调用API
        try:
            messages = [{'role': 'user', 'content': message}]
            response = self.call_deepseek_api(messages, api_key)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'API调用失败: {response.text}'
                }
            
            result = response.json()
            
            # 提取响应和token使用信息
            usage = result.get('usage', {})
            assistant_message = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            # 保存token使用记录
            self.save_token_usage(user_id, usage)
            
            return {
                'success': True,
                'message': assistant_message,
                'usage': {
                    'prompt_tokens': usage.get('prompt_tokens', 0),
                    'completion_tokens': usage.get('completion_tokens', 0),
                    'total_tokens': usage.get('total_tokens', 0)
                }
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except Exception as e:
            print(f"Process chat error: {e}")
            return {
                'success': False,
                'error': f'处理请求时出错: {str(e)}'
            }
    
    def process_chat_stream(self, user_id, message):
        """处理流式聊天请求，返回生成器（已废弃，建议使用process_chat_stream_with_session）"""
        # 获取API key
        api_key = self.get_active_api_key()
        if not api_key:
            yield f"data: {json.dumps({'type': 'error', 'message': '未配置API key'})}\n\n"
            return
        
        # 调用流式API
        try:
            messages = [{'role': 'user', 'content': message}]
            response = self.call_deepseek_api(messages, api_key, stream=True)
            
            if response.status_code != 200:
                error_text = response.text
                yield f"data: {json.dumps({'type': 'error', 'message': f'API调用失败: {error_text}'})}\n\n"
                return
            
            # 解析流式响应
            usage = None
            for line in response.iter_lines():
                if not line:
                    continue
                
                # 移除 'data: ' 前缀
                if line.startswith(b'data: '):
                    line = line[6:]
                
                # 检查是否结束
                if line.strip() == b'[DONE]':
                    break
                
                try:
                    data = json.loads(line.decode('utf-8'))
                    
                    # 提取usage信息（可能在顶层，通常在最后一条消息中）
                    if 'usage' in data:
                        usage = data['usage']
                    
                    # 提取内容增量
                    choices = data.get('choices', [])
                    if choices:
                        delta = choices[0].get('delta', {})
                        content = delta.get('content', '')
                        if content:
                            yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                    
                except json.JSONDecodeError:
                    continue
            
            # 保存token使用记录
            if usage:
                self.save_token_usage(user_id, usage)
                yield f"data: {json.dumps({'type': 'usage', 'usage': usage})}\n\n"
            else:
                # 如果没有收到usage信息，发送完成信号（可能API没有返回usage）
                print("Warning: No usage information received from stream response")
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except requests.exceptions.RequestException as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'网络请求失败: {str(e)}'})}\n\n"
        except Exception as e:
            print(f"Process chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时出错: {str(e)}'})}\n\n"
    
    def create_session(self, user_id, title=None):
        """创建新的聊天会话
        
        Args:
            user_id: 用户ID
            title: 会话主题，如果为None则自动生成
            
        Returns:
            会话ID
        """
        db = get_session()
        try:
            if not title:
                title = "新对话"
            
            session = ChatSession(
                user_id=user_id,
                title=title
            )
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
    
    def save_message(self, session_id, role, content):
        """保存聊天消息
        
        Args:
            session_id: 会话ID
            role: 角色 ('user' 或 'assistant')
            content: 消息内容
        """
        db = get_session()
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content
            )
            db.add(message)
            db.commit()
        except Exception as e:
            print(f"Save message error: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_sessions(self, user_id, limit=50):
        """获取用户的会话列表
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            会话列表
        """
        db = get_session()
        try:
            sessions = db.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).order_by(
                ChatSession.updated_at.desc()
            ).limit(limit).all()
            
            return [{
                'id': s.id,
                'title': s.title,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'updated_at': s.updated_at.isoformat() if s.updated_at else None
            } for s in sessions]
        except Exception as e:
            print(f"Get sessions error: {e}")
            return []
        finally:
            db.close()
    
    def get_session_messages(self, session_id, user_id):
        """获取会话的所有消息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（用于验证权限）
            
        Returns:
            消息列表，格式为 [{'role': 'user', 'content': '...'}, ...]
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
            
            return [{
                'role': m.role,
                'content': m.content
            } for m in messages]
        except Exception as e:
            print(f"Get session messages error: {e}")
            return None
        finally:
            db.close()
    
    def update_session_title(self, session_id, user_id, title):
        """更新会话主题
        
        Args:
            session_id: 会话ID
            user_id: 用户ID（用于验证权限）
            title: 新主题
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
    
    def generate_title_from_message(self, message):
        """从第一条消息生成会话主题
        
        Args:
            message: 用户的第一条消息
            
        Returns:
            生成的主题（最多30个字符）
        """
        if not message:
            return "新对话"
        
        # 简单处理：取前30个字符作为主题
        title = message.strip()[:30]
        if len(message) > 30:
            title += "..."
        return title
    
    def process_chat_stream_with_session(self, user_id, session_id, message):
        """处理带会话的流式聊天请求
        
        Args:
            user_id: 用户ID
            session_id: 会话ID（如果为None则创建新会话）
            message: 用户消息
            
        Yields:
            SSE格式的数据流
        """
        try:
            # 如果session_id为None，创建新会话
            if not session_id:
                title = self.generate_title_from_message(message)
                session_id = self.create_session(user_id, title)
                if not session_id:
                    yield f"data: {json.dumps({'type': 'error', 'message': '创建会话失败'})}\n\n"
                    return
                # 发送会话ID给前端
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
            
            # 获取历史消息
            history_messages = self.get_session_messages(session_id, user_id)
            if history_messages is None:
                yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在或无权限'})}\n\n"
                return
            
            # 只保留最近5对对话（即最近10条消息，user-assistant成对）
            # 如果历史消息数量超过10条，只保留最后10条
            if len(history_messages) > 10:
                history_messages = history_messages[-10:]
            
            # 构建消息列表（包含system提示词、历史消息和当前消息）
            api_messages = []
            
            # 添加system角色提示词
            system_prompt = "你是一个友好、专业且乐于助人的AI助手。你的目标是提供准确、有用和清晰的信息，帮助用户解决问题。请用简洁明了的语言回答，如果遇到不确定的问题，请诚实说明。"
            api_messages.append({
                'role': 'system',
                'content': system_prompt
            })
            
            # 添加历史消息
            for msg in history_messages:
                api_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # 添加当前用户消息
            api_messages.append({
                'role': 'user',
                'content': message
            })
            
            # 保存用户消息
            self.save_message(session_id, 'user', message)
            
            # 获取API key
            api_key = self.get_active_api_key()
            if not api_key:
                yield f"data: {json.dumps({'type': 'error', 'message': '未配置API key'})}\n\n"
                return
            
            # 调用流式API
            try:
                response = self.call_deepseek_api(api_messages, api_key, stream=True)
                
                if response.status_code != 200:
                    error_text = response.text
                    yield f"data: {json.dumps({'type': 'error', 'message': f'API调用失败: {error_text}'})}\n\n"
                    return
                
                # 解析流式响应
                usage = None
                assistant_content = ''
                
                for line in response.iter_lines(decode_unicode=False):
                    if not line:
                        continue
                    
                    # 只处理以 'data: ' 开头的SSE数据行，跳过HTTP响应头
                    if not line.startswith(b'data: '):
                        continue
                    
                    # 移除 'data: ' 前缀
                    line = line[6:]
                    
                    # 检查是否结束
                    if line.strip() == b'[DONE]':
                        break
                    
                    # 跳过空行
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line.decode('utf-8'))
                        
                        # 提取usage信息
                        if 'usage' in data:
                            usage = data['usage']
                        
                        # 提取内容增量
                        choices = data.get('choices', [])
                        if choices:
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                assistant_content += content
                                yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                        
                    except json.JSONDecodeError:
                        continue
                
                # 保存AI回复
                if assistant_content:
                    self.save_message(session_id, 'assistant', assistant_content)
                
                # 保存token使用记录
                if usage:
                    self.save_token_usage(user_id, usage)
                    yield f"data: {json.dumps({'type': 'usage', 'usage': usage})}\n\n"
                
                # 如果是新会话且只有一条用户消息，更新主题
                if history_messages == []:
                    title = self.generate_title_from_message(message)
                    self.update_session_title(session_id, user_id, title)
                    yield f"data: {json.dumps({'type': 'session_title', 'title': title})}\n\n"
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except requests.exceptions.RequestException as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'网络请求失败: {str(e)}'})}\n\n"
            except Exception as e:
                print(f"Process chat stream with session error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时出错: {str(e)}'})}\n\n"
        except Exception as e:
            print(f"Process chat stream with session outer error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'处理请求时出错: {str(e)}'})}\n\n"

