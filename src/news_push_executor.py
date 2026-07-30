"""
每日新闻推送任务执行器
这个模块负责实际的新闻搜索和推送逻辑，与定时任务解耦
"""
from tools.news_search_tool import search_ai_news_func, search_autonomous_driving_news_func
from tools.feishu_message_tool import send_daily_news_func


def execute_daily_news_push():
    """
    执行每日新闻推送任务
    由定时任务调度器调用
    """
    try:
        # 1. 搜索 AI 新闻（3条）
        ai_news = search_ai_news_func(query="人工智能 AI 大模型 最新进展", count=3)

        # 2. 搜索自动驾驶新闻（3条）
        auto_news = search_autonomous_driving_news_func(query="自动驾驶 无人驾驶 L4 L3 最新进展", count=3)

        # 3. 推送合并后的新闻到飞书
        result = send_daily_news_func(ai_news=ai_news, auto_news=auto_news)

        return result

    except Exception as e:
        return f"每日新闻推送失败: {str(e)}"
