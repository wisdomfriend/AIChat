"""百度搜索服务"""
import requests
from bs4 import BeautifulSoup
import urllib.parse
from typing import List, Dict
import time
from ..config import Config


class BaiduSearchService:
    """百度搜索服务"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        # 使用 Session 来保持 Cookie，模拟浏览器行为
        self.session = requests.Session()
        # 延迟初始化：不在 __init__ 中立即访问百度，而是在第一次使用时再初始化
        self._session_initialized = False
    
    def search(self, query: str, num_results: int = 3) -> str:
        """
        执行百度搜索并返回格式化结果
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量（默认3条）
            
        Returns:
            格式化的搜索结果文本
        """
        try:
            # 确保会话已初始化（延迟初始化）
            self._ensure_session_initialized()
            
            # 使用爬取方式搜索
            results = self._search_with_scraping(query, num_results)
            
            if not results:
                return "未找到相关搜索结果。"
            
            # 格式化结果
            formatted = "【搜索结果】\n\n"
            for i, result in enumerate(results, 1):
                formatted += f"{i}. {result['title']}\n"
                formatted += f"   {result['snippet']}\n"
                if result.get('url'):
                    formatted += f"   链接: {result['url']}\n"
                formatted += "\n"
            
            return formatted
            
        except Exception as e:
            print(f"Baidu search error: {e}")
            return f"搜索过程中出现错误: {str(e)}"
    
    def _ensure_session_initialized(self):
        """
        确保会话已初始化（延迟初始化）
        只在第一次使用时才访问百度首页获取 Cookie
        """
        if self._session_initialized:
            return
        
        # 尝试初始化，只有成功时才标记为已初始化
        if self._init_session():
            self._session_initialized = True
    
    def _init_session(self):
        """
        初始化会话，访问首页获取 Cookie
        
        工作原理：
        1. 向百度首页发送 GET 请求
        2. 百度服务器返回响应，并在响应头中设置 Cookie（Set-Cookie）
        3. requests.Session 自动保存这些 Cookie 到 self.session.cookies
        4. 后续所有使用 self.session 的请求都会自动携带这些 Cookie
        
        常见的百度 Cookie：
        - BAIDUID: 百度用户唯一标识
        - BIDUPSID: 百度 ID
        - PSTM: 首次访问时间戳
        - H_PS_PSSID: 会话 ID
        
        这样做的好处：
        - 模拟真实浏览器行为，降低被反爬虫系统识别的风险
        - 服务器可能根据 Cookie 判断是否为正常访问
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 增加重试机制
        max_retries = 2
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br, zstd',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                # 访问首页获取 Cookie，增加超时时间到15秒
                # 服务器返回的 Cookie 会被自动保存到 self.session.cookies 中
                response = self.session.get('https://www.baidu.com', headers=headers, timeout=15)
                
                # 如果成功，返回 True
                if response.status_code == 200:
                    # 可选：打印获取到的 Cookie（用于调试）
                    # logger.debug(f"获取到的 Cookie 数量: {len(self.session.cookies)}")
                    return True
                else:
                    logger.warning(f"百度首页返回状态码: {response.status_code}")
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    logger.debug(f"百度搜索服务初始化超时，正在重试 ({attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.warning("百度搜索服务初始化超时（不影响其他功能）")
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    logger.debug(f"百度搜索服务连接失败，正在重试 ({attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                    continue
                else:
                    # 连接错误（包括连接重置）不影响其他功能，只记录警告
                    logger.warning(f"百度搜索服务初始化失败（不影响其他功能）: {e}")
            except Exception as e:
                # 其他异常也只记录警告，不影响其他功能
                logger.warning(f"百度搜索服务初始化失败（不影响其他功能）: {e}")
                break
        
        # 所有重试都失败，返回 False
        return False
    
    def _search_with_scraping(self, query: str, num_results: int) -> List[Dict]:
        """使用百度网页端搜索（桌面端HTML解析）"""
        try:
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.baidu.com/s?wd={encoded_query}"
            
            # 使用与浏览器完全一致的请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',  # 支持 Brotli，需要安装 brotli 库
                'Referer': 'https://www.baidu.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
            }
            
            # 使用 session 发送请求，自动携带 Cookie
            response = self.session.get(search_url, headers=headers, timeout=15, allow_redirects=True)
            
            # 检查响应内容是否被正确解压
            # 如果 Content-Encoding 是 br，但 response.text 看起来是乱码，需要手动解压
            content_encoding = response.headers.get('Content-Encoding', '').lower()
            
            # 检查 response.text 的前几个字符，判断是否是未解压的压缩数据
            # 如果前两个字节是 \x1f\x00 或其他不可打印字符，可能是未解压的 Brotli
            if response.content and len(response.content) > 2:
                content_start = response.content[:2]
                is_compressed = False
                compress_type = None
                
                # 检查是否是 gzip (魔数 \x1f\x8b)
                if content_start == b'\x1f\x8b':
                    is_compressed = True
                    compress_type = 'gzip'
                # 检查是否是 brotli (可能以 \x1f\x00 或其他格式开头)
                elif content_encoding == 'br' or (content_start[0] == 0x1f and content_start[1] in [0x00, 0x81, 0x8b]):
                    is_compressed = True
                    compress_type = 'br'
                
                # 如果检测到压缩数据，尝试手动解压
                if is_compressed:
                    try:
                        if compress_type == 'gzip':
                            import gzip
                            decompressed = gzip.decompress(response.content)
                            response._content = decompressed
                            print("Manually decompressed gzip content")
                        elif compress_type == 'br':
                            import brotli
                            decompressed = brotli.decompress(response.content)
                            response._content = decompressed
                            print("Manually decompressed brotli content")
                        # 重新设置编码
                        response.encoding = 'utf-8'
                    except Exception as e:
                        print(f"Manual decompress error ({compress_type}): {e}")
                        # 如果解压失败，尝试不使用 br 重新请求
                        if compress_type == 'br':
                            print("Retrying without br compression")
                            headers['Accept-Encoding'] = 'gzip, deflate'
                            response = self.session.get(search_url, headers=headers, timeout=15, allow_redirects=True)
            
            # 确保正确设置编码
            if response.encoding is None or response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding or 'utf-8'
            
            if response.status_code != 200:
                print(f"Baidu search HTTP error: {response.status_code}")
                return []
            
            # 检查是否返回了错误页面
            if '网络不给力' in response.text or '问题反馈' in response.text:
                print("Baidu returned error page")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # 尝试多种选择器来匹配百度搜索结果
            # 百度搜索结果可能在不同的容器中
            result_divs = []
            
            # 尝试不同的选择器
            result_divs.extend(soup.find_all('div', class_='result'))
            result_divs.extend(soup.find_all('div', class_='c-container'))
            result_divs.extend(soup.find_all('div', {'id': lambda x: x and x.startswith('1')}))
            result_divs.extend(soup.find_all('div', class_='c-result'))
            
            # 去重（基于元素对象）
            seen = set()
            unique_divs = []
            for div in result_divs:
                if id(div) not in seen:
                    seen.add(id(div))
                    unique_divs.append(div)
            result_divs = unique_divs
            
            # 如果没找到结果，尝试更通用的选择器
            if not result_divs:
                # 查找包含链接的div，通常搜索结果都有链接
                all_divs = soup.find_all('div')
                for div in all_divs:
                    # 检查是否包含标题和链接
                    if div.find('h3') and div.find('a', href=True):
                        result_divs.append(div)
            
            for div in result_divs:
                if len(results) >= num_results:
                    break
                    
                try:
                    # 提取标题 - 尝试多种方式
                    title_elem = (
                        div.find('h3') or
                        div.find('a', class_='c-title-text') or
                        div.find('a', class_='c-title') or
                        div.find('h3', class_='t') or
                        div.find('a', href=True)
                    )
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    if not title:
                        continue
                    
                    # 提取链接
                    link_elem = title_elem if title_elem.name == 'a' else div.find('a', href=True)
                    url = ''
                    if link_elem and link_elem.get('href'):
                        url = link_elem['href']
                        # 处理百度跳转链接
                        if url.startswith('/link?url='):
                            # 这是百度的跳转链接，需要解码
                            try:
                                from urllib.parse import unquote
                                url = unquote(url.split('url=')[1].split('&')[0])
                            except:
                                pass
                        elif not url.startswith('http'):
                            url = 'https://www.baidu.com' + url
                    
                    # 提取摘要 - 尝试多种方式
                    snippet_elem = (
                        div.find('span', class_='content-right') or
                        div.find('div', class_='c-abstract') or
                        div.find('span', class_='c-abstract') or
                        div.find('div', class_='c-span9') or
                        div.find('span', class_='c-color-text') or
                        div.find('div', class_='c-row')
                    )
                    
                    snippet = ''
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                        # 清理摘要文本
                        snippet = ' '.join(snippet.split())
                    
                    # 如果还是没有摘要，尝试从父元素获取
                    if not snippet:
                        parent = div.find_parent()
                        if parent:
                            text_parts = []
                            for elem in parent.find_all(['span', 'div', 'p']):
                                text = elem.get_text(strip=True)
                                if text and len(text) > 20 and title not in text:
                                    text_parts.append(text)
                            if text_parts:
                                snippet = text_parts[0][:200]
                    
                    results.append({
                        'title': title,
                        'snippet': snippet[:200] if snippet else '暂无摘要',
                        'url': url
                    })
                except Exception as e:
                    print(f"Parse search result error: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Baidu search error: {e}")
            import traceback
            traceback.print_exc()
            return []

