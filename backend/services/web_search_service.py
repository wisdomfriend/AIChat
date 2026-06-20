"""联网搜索聚合 Service（Tavily + 百度）。

职责总览：
- `WebSearchService.search()`  并行调用 Tavily 与百度搜索，合并结果后返回格式化文本
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

from ..config import Config
from .baidu_search_service import BaiduSearchService
from .tavily_search_service import TavilySearchService


class WebSearchService:
    """并行执行 Tavily 与百度搜索，合并去重后返回统一格式文本。"""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.tavily_service = TavilySearchService(self.config)
        self.baidu_service = BaiduSearchService(self.config)

    def search(self, query: str, num_results: int = None) -> str:
        """并行搜索并合并 Tavily、百度结果。"""
        tavily_num = num_results or self.config.TAVILY_SEARCH_MAX_RESULTS
        baidu_num = num_results or self.config.BAIDU_SEARCH_MAX_RESULTS

        tavily_results: List[Dict] = []
        baidu_results: List[Dict] = []

        with ThreadPoolExecutor(max_workers=2) as executor:
            tavily_future = executor.submit(self.tavily_service.search_results, query, tavily_num)
            baidu_future = executor.submit(self.baidu_service.search_results, query, baidu_num)

            try:
                tavily_results = tavily_future.result()
            except Exception as e:
                print(f"Tavily search error: {e}")

            try:
                baidu_results = baidu_future.result()
            except Exception as e:
                print(f"Baidu search error: {e}")

        merged = self._merge_results(tavily_results, baidu_results)
        if not merged:
            return "未找到相关搜索结果。"

        return self._format_results(merged)

    def _merge_results(
        self,
        tavily_results: List[Dict],
        baidu_results: List[Dict],
    ) -> List[Dict]:
        merged: List[Dict] = []
        seen_urls = set()

        for result in tavily_results + baidu_results:
            normalized = self._normalize_result(result)
            url_key = normalized.get("url", "").strip().lower().rstrip("/")
            if url_key and url_key in seen_urls:
                continue
            if url_key:
                seen_urls.add(url_key)
            merged.append(normalized)

        return merged

    @staticmethod
    def _normalize_result(result: Dict) -> Dict:
        source = result.get("source") or "未知来源"
        return {
            "source": source,
            "title": result.get("title") or "无标题",
            "snippet": (
                result.get("snippet")
                or result.get("content")
                or "暂无摘要"
            ),
            "url": result.get("url") or "",
        }

    @staticmethod
    def _format_results(results: List[Dict]) -> str:
        formatted = "【联网搜索结果】\n\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. [{result['source']}] {result['title']}\n"
            formatted += f"   {result['snippet']}\n"
            if result.get("url"):
                formatted += f"   链接: {result['url']}\n"
            formatted += "\n"
        return formatted
