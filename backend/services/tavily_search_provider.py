"""Tavily 联网搜索 Provider。

职责总览：
- `TavilySearchProvider.search_results()`  返回结构化结果，供 WebSearchService 聚合
- `TavilySearchProvider.search()`  返回格式化文本（独立调用时使用）
"""
from typing import Any, Dict, List

from ..config import Config


class TavilySearchProvider:
    """通过 langchain_tavily.TavilySearch 调用 Tavily Search API。"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self._search_tool = None
        if self.config.TAVILY_API_KEY:
            self._search_tool = self._create_search_tool(
                self.config.TAVILY_SEARCH_MAX_RESULTS,
                self.config.TAVILY_API_KEY,
            )

    @staticmethod
    def _create_search_tool(max_results: int, api_key: str):
        from langchain_tavily import TavilySearch

        return TavilySearch(max_results=max_results, tavily_api_key=api_key)

    def _get_search_tool(self, num_results: int = None):
        if not self.config.TAVILY_API_KEY:
            return None
        if num_results is not None and num_results != self.config.TAVILY_SEARCH_MAX_RESULTS:
            return self._create_search_tool(num_results, self.config.TAVILY_API_KEY)
        if self._search_tool is None:
            self._search_tool = self._create_search_tool(
                self.config.TAVILY_SEARCH_MAX_RESULTS,
                self.config.TAVILY_API_KEY,
            )
        return self._search_tool

    def search_results(self, query: str, num_results: int = None) -> List[Dict]:
        """执行 Tavily 搜索并返回结构化结果列表。"""
        try:
            search_tool = self._get_search_tool(num_results)
            if search_tool is None:
                return []

            data = search_tool.invoke({"query": query})
            raw_results = self._extract_results(data)
            return [self._normalize_result(item) for item in raw_results]
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []

    def search(self, query: str, num_results: int = None) -> str:
        """执行 Tavily 搜索并返回格式化文本。"""
        try:
            results = self.search_results(query, num_results)
            if not results:
                return "未找到相关搜索结果。"
            return self._format_results(results, title="【Tavily 搜索结果】")
        except Exception as e:
            print(f"Tavily search error: {e}")
            return f"搜索过程中出现错误: {str(e)}"

    @staticmethod
    def _extract_results(data: Any) -> List[Dict]:
        if isinstance(data, dict):
            results = data.get("results", data)
        else:
            results = data

        if isinstance(results, dict):
            return [results]
        if isinstance(results, list):
            return results
        return []

    @staticmethod
    def _normalize_result(result: Dict) -> Dict:
        return {
            "source": "Tavily",
            "title": result.get("title") or "无标题",
            "snippet": result.get("content") or result.get("snippet") or "暂无摘要",
            "url": result.get("url") or "",
        }

    @staticmethod
    def _format_results(results: List[Dict], title: str = "【搜索结果】") -> str:
        formatted = f"{title}\n\n"
        for i, result in enumerate(results, 1):
            label = result.get("source")
            prefix = f"[{label}] " if label else ""
            formatted += f"{i}. {prefix}{result.get('title') or '无标题'}\n"
            formatted += f"   {result.get('snippet') or result.get('content') or '暂无摘要'}\n"
            url = result.get("url") or ""
            if url:
                formatted += f"   链接: {url}\n"
            formatted += "\n"

        return formatted
