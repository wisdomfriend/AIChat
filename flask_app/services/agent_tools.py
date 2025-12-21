"""LangChain Agent 工具定义 - 包括网络搜索等工具"""
import requests
import json
import re
from typing import Optional, Type
from langchain_core.tools import tool
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class BaiduSearchInput(BaseModel):
    """百度搜索工具的输入参数"""
    query: str = Field(description="搜索查询关键词")


class BaiduSearchTool(BaseTool):
    """百度搜索工具 - 使用百度搜索API进行网络搜索"""
    
    name: str = "baidu_search"
    description: str = (
        "使用百度搜索引擎搜索网络信息。"
        "当你需要获取最新的网络信息、新闻、实时数据或无法从已有知识中回答的问题时，使用此工具。"
        "输入应该是搜索关键词或查询语句。"
    )
    args_schema: Type[BaseModel] = BaiduSearchInput
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        初始化百度搜索工具
        
        Args:
            api_key: 百度搜索API密钥（可选，如果不提供则使用网页搜索）
            api_url: 百度搜索API地址（可选）
        """
        super().__init__()
        self.api_key = api_key
        self.api_url = api_url or "https://www.baidu.com/s"
    
    def _run(self, query: str) -> str:
        """
        执行百度搜索
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果摘要
        """
        try:
            # 如果有API密钥，使用API接口
            if self.api_key:
                return self._search_with_api(query)
            else:
                # 否则使用网页搜索（简单实现）
                return self._search_web(query)
        except Exception as e:
            return f"搜索失败: {str(e)}"
    
    def _search_with_api(self, query: str) -> str:
        """使用百度搜索API进行搜索"""
        # 注意：这里需要根据百度开放平台的实际API文档来实现
        # 以下是示例实现，实际使用时需要替换为真实的API接口
        try:
            params = {
                "wd": query,
                "apikey": self.api_key
            }
            response = requests.get(self.api_url, params=params, timeout=10)
            if response.status_code == 200:
                # 解析搜索结果（需要根据实际API响应格式调整）
                data = response.json()
                # 提取前几个结果的标题和摘要
                results = []
                if isinstance(data, dict) and 'results' in data:
                    for item in data['results'][:5]:  # 取前5个结果
                        title = item.get('title', '')
                        snippet = item.get('snippet', '')
                        results.append(f"标题: {title}\n摘要: {snippet}")
                return "\n\n".join(results) if results else "未找到相关结果"
            else:
                return f"API请求失败，状态码: {response.status_code}"
        except Exception as e:
            return f"API搜索出错: {str(e)}"
    
    def _search_web(self, query: str) -> str:
        """
        使用网页搜索并解析结果
        
        注意：这是一个简化的实现，实际生产环境建议使用：
        1. 百度开放平台的搜索API
        2. 或其他专业的搜索API服务（如SerpAPI、Google Custom Search等）
        """
        try:
            # 使用百度网页搜索
            params = {"wd": query}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = requests.get(self.api_url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                results = []
                
                if HAS_BS4:
                    # 使用 BeautifulSoup 解析
                    soup = BeautifulSoup(html, 'html.parser')
                    # 查找搜索结果（百度搜索结果通常在特定的 div 中）
                    result_divs = soup.find_all('div', class_='result')
                    if not result_divs:
                        # 尝试其他可能的类名
                        result_divs = soup.find_all('div', {'data-log': re.compile('.*')})
                    
                    for i, div in enumerate(result_divs[:5], 1):  # 只取前5个结果
                        title_elem = div.find('h3') or div.find('a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            # 查找摘要
                            abstract_elem = div.find('span', class_='content-right_8Zs40') or \
                                          div.find('div', class_='c-abstract') or \
                                          div.find('span', class_='content')
                            abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
                            if title:
                                results.append(f"{i}. {title}\n   {abstract[:200] if abstract else '无摘要'}")
                else:
                    # 如果没有 BeautifulSoup，使用正则表达式简单提取
                    # 提取标题（在 <h3> 标签中）
                    title_pattern = r'<h3[^>]*>(.*?)</h3>'
                    titles = re.findall(title_pattern, html, re.DOTALL)
                    for i, title_html in enumerate(titles[:5], 1):
                        # 清理 HTML 标签
                        title = re.sub(r'<[^>]+>', '', title_html).strip()
                        if title:
                            results.append(f"{i}. {title}")
                
                if results:
                    return f"搜索关键词: {query}\n\n找到 {len(results)} 条结果:\n\n" + "\n\n".join(results)
                else:
                    return f"搜索关键词: {query}\n\n未找到相关结果，或搜索结果格式无法解析。\n注意: 建议安装 beautifulsoup4 以获得更好的搜索结果解析。"
            else:
                return f"搜索请求失败，状态码: {response.status_code}"
        except Exception as e:
            return f"网页搜索出错: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """异步执行搜索"""
        # 对于搜索工具，异步实现可以复用同步实现
        return self._run(query)


# 使用 @tool 装饰器的简化版本（推荐用于简单场景）
@tool
def baidu_search_simple(query: str) -> str:
    """
    使用百度搜索引擎搜索网络信息。
    
    当你需要获取最新的网络信息、新闻、实时数据或无法从已有知识中回答的问题时，使用此工具。
    
    Args:
        query: 搜索查询关键词
        
    Returns:
        搜索结果摘要
    """
    try:
        # 使用百度网页搜索
        url = "https://www.baidu.com/s"
        params = {"wd": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            results = []
            
            if HAS_BS4:
                # 使用 BeautifulSoup 解析
                soup = BeautifulSoup(html, 'html.parser')
                result_divs = soup.find_all('div', class_='result')
                if not result_divs:
                    result_divs = soup.find_all('div', {'data-log': re.compile('.*')})
                
                for i, div in enumerate(result_divs[:5], 1):
                    title_elem = div.find('h3') or div.find('a')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        abstract_elem = div.find('span', class_='content-right_8Zs40') or \
                                      div.find('div', class_='c-abstract') or \
                                      div.find('span', class_='content')
                        abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""
                        if title:
                            results.append(f"{i}. {title}\n   {abstract[:200] if abstract else '无摘要'}")
            else:
                # 使用正则表达式简单提取
                title_pattern = r'<h3[^>]*>(.*?)</h3>'
                titles = re.findall(title_pattern, html, re.DOTALL)
                for i, title_html in enumerate(titles[:5], 1):
                    title = re.sub(r'<[^>]+>', '', title_html).strip()
                    if title:
                        results.append(f"{i}. {title}")
            
            if results:
                return f"搜索关键词: {query}\n\n找到 {len(results)} 条结果:\n\n" + "\n\n".join(results)
            else:
                return f"搜索关键词: {query}\n\n未找到相关结果，或搜索结果格式无法解析。\n注意: 建议安装 beautifulsoup4 以获得更好的搜索结果解析。"
        else:
            return f"搜索请求失败，状态码: {response.status_code}"
    except Exception as e:
        return f"搜索出错: {str(e)}"


def create_baidu_search_tool(api_key: Optional[str] = None, api_url: Optional[str] = None) -> BaiduSearchTool:
    """
    创建百度搜索工具实例
    
    Args:
        api_key: 百度搜索API密钥（可选）
        api_url: 百度搜索API地址（可选）
        
    Returns:
        BaiduSearchTool 实例
    """
    return BaiduSearchTool(api_key=api_key, api_url=api_url)

