"""聊天服务"""
import json
import requests
from ..database import get_session
from ..models import ApiKey, TokenUsage
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
    
    def call_deepseek_api(self, message, api_key, stream=False):
        """调用DeepSeek API"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        payload = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'user', 'content': message}
            ],
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
            response = self.call_deepseek_api(message, api_key)
            
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
        """处理流式聊天请求，返回生成器"""
        # 获取API key
        api_key = self.get_active_api_key()
        if not api_key:
            yield f"data: {json.dumps({'type': 'error', 'message': '未配置API key'})}\n\n"
            return
        
        # 调用流式API
        try:
            response = self.call_deepseek_api(message, api_key, stream=True)
            
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

