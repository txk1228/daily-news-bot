"""
新闻搜索工具 - 获取科技/AI和自动驾驶相关新闻
"""
from langchain.tools import tool
from coze_coding_dev_sdk import SearchClient
from coze_coding_utils.runtime_ctx.context import new_context


def _search_news_impl(query: str, count: int = 3) -> str:
    """
    搜索新闻的实现函数（核心逻辑）

    Args:
        query: 搜索关键词
        count: 返回的新闻条数，默认3条

    Returns:
        格式化的新闻列表，每条包含标题、摘要、来源和链接
    """
    ctx = new_context(method="search.news")
    client = SearchClient(ctx=ctx)

    try:
        response = client.web_search(
            query=query,
            count=count,
            need_summary=True
        )

        if not response.web_items:
            return f"未找到关于「{query}」的最新新闻"

        results = []
        for i, item in enumerate(response.web_items, 1):
            title = item.title or "无标题"
            source = item.site_name or "未知来源"
            url = item.url or ""
            snippet = item.snippet or item.summary or ""
            # 限制摘要长度
            snippet = snippet[:100] + "..." if len(snippet) > 100 else snippet

            results.append(f"【{title}】📝 {snippet}📍 来源：{source}🔗 原文链接：{url}")

        return "\n".join(results)

    except Exception as e:
        return f"搜索失败: {str(e)}"


@tool
def search_ai_news(count: int = 3) -> str:
    """
    搜索人工智能领域的最新新闻和动态。

    Args:
        count: 返回的新闻条数，默认3条

    Returns:
        格式化的AI领域新闻列表
    """
    return _search_news_impl(query="人工智能 AI 大模型 最新进展", count=count)


@tool
def search_autonomous_driving_news(count: int = 3) -> str:
    """
    搜索自动驾驶领域的最新新闻和动态。

    Args:
        count: 返回的新闻条数，默认3条

    Returns:
        格式化的自动驾驶新闻列表
    """
    return _search_news_impl(query="自动驾驶 无人驾驶 L4 L3 最新进展", count=count)


@tool
def search_tech_industry_news(count: int = 3) -> str:
    """
    搜索科技行业动态和重要事件。

    Args:
        count: 返回的新闻条数，默认3条

    Returns:
        格式化的科技行业新闻列表
    """
    return _search_news_impl(query="科技行业 互联网 最新动态", count=count)


# 用于直接调用的非装饰函数（供 executor 使用）
def search_ai_news_func(query: str = "人工智能 AI 大模型 最新进展", count: int = 3) -> str:
    return _search_news_impl(query=query, count=count)


def search_autonomous_driving_news_func(query: str = "自动驾驶 无人驾驶 L4 L3 最新进展", count: int = 3) -> str:
    return _search_news_impl(query=query, count=count)


def search_tech_industry_news_func(query: str = "科技行业 互联网 最新动态", count: int = 3) -> str:
    return _search_news_impl(query=query, count=count)
