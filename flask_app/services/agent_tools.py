"""Agent 工具定义 — 供 create_agent 使用。"""
from datetime import datetime

import pytz
from langchain_core.tools import tool
from langgraph.config import get_stream_writer


def build_agent_tools(search_service):
    """构建 Agent 工具列表（注入 search_service）。"""

    @tool
    def web_search(query: str) -> str:
        """搜索互联网获取最新信息。当用户询问新闻、价格、天气、实时数据或需要联网验证的问题时使用。"""
        writer = get_stream_writer()
        if writer:
            writer({"type": "tool_status", "tool": "web_search", "status": "start", "message": "正在搜索..."})
        try:
            result = search_service.search(query=query)
        except Exception as e:
            result = f"搜索失败: {str(e)}"
        if writer:
            writer({"type": "tool_status", "tool": "web_search", "status": "done", "message": "搜索完成"})
        return result

    @tool
    def get_time_info() -> str:
        """获取当前北京时间（日期、时刻、星期）。当用户询问现在几点、今天日期等问题时使用。"""
        writer = get_stream_writer()
        if writer:
            writer({"type": "tool_status", "tool": "get_time_info", "status": "start", "message": "正在查询时间..."})
        try:
            tz = pytz.timezone("Asia/Shanghai")
            now = datetime.now(tz)
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            result = (
                f"当前时间：{now.strftime('%Y年%m月%d日')} "
                f"{now.strftime('%H:%M:%S')} {weekdays[now.weekday()]}"
            )
        except Exception as e:
            result = f"获取时间信息失败: {str(e)}"
        if writer:
            writer({"type": "tool_status", "tool": "get_time_info", "status": "done", "message": "查询完成"})
        return result

    return [web_search, get_time_info]
