"""
飞书消息推送工具 - 发送每日新闻到飞书群
"""
import requests
import json
from datetime import datetime
from langchain.tools import tool
from coze_workload_identity import Client


def _get_webhook_url() -> str:
    """获取飞书群机器人的 webhook URL"""
    client = Client()
    credential = client.get_integration_credential("integration-feishu-message")
    credential_data = json.loads(credential)
    return credential_data["webhook_url"]


def _build_daily_news_message(ai_news: str, auto_news: str) -> str:
    """
    构建每日新闻推送的完整消息内容

    Args:
        ai_news: AI领域新闻
        auto_news: 自动驾驶新闻

    Returns:
        格式化的完整消息
    """
    today = datetime.now().strftime("%Y年%m月%d日")

    # 构建完整消息
    message_parts = [
        f"小可早上好呀～🥰今天是{today}，你的科技 & 自动驾驶行业日报已送达，帮你整理好了新鲜资讯，快速跟上行业动态！",
        "====================================================",
        "🤖 AI 人工智能行业",
        ai_news if ai_news else "暂无最新资讯",
        "====================================================",
        "🚗 自动驾驶行业",
        auto_news if auto_news else "暂无最新资讯",
        "====================================================",
        "新的一天也要元气满满，一起解锁更多进步！✨"
    ]

    return "\n".join(message_parts)


def _send_text_impl(text: str) -> str:
    """发送文本消息的实现函数"""
    try:
        payload = {
            "msg_type": "text",
            "content": {"text": text}
        }

        response = requests.post(_get_webhook_url(), json=payload)
        result = response.json()

        if result.get("code") == 0:
            return "✅ 消息发送成功"
        else:
            return f"❌ 消息发送失败: {result.get('msg', '未知错误')}"

    except Exception as e:
        return f"❌ 发送失败: {str(e)}"


@tool
def send_text_message(text: str) -> str:
    """
    发送文本消息到飞书群。

    Args:
        text: 要发送的文本内容

    Returns:
        发送结果
    """
    return _send_text_impl(text)


@tool
def send_rich_text_message(title: str, content: str) -> str:
    """
    发送富文本消息到飞书群。

    Args:
        title: 消息标题
        content: 消息内容，支持换行和链接

    Returns:
        发送结果
    """
    try:
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [
                            [
                                {"tag": "text", "text": content}
                            ]
                        ]
                    }
                }
            }
        }

        response = requests.post(_get_webhook_url(), json=payload)
        result = response.json()

        if result.get("code") == 0:
            return "✅ 富文本消息发送成功"
        else:
            return f"❌ 富文本消息发送失败: {result.get('msg', '未知错误')}"

    except Exception as e:
        return f"❌ 发送失败: {str(e)}"


@tool
def send_news_card(title: str, news_items: str) -> str:
    """
    发送交互式卡片消息到飞书群，用于推送新闻。

    Args:
        title: 卡片标题
        news_items: 新闻内容

    Returns:
        发送结果
    """
    try:
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": news_items
                        }
                    }
                ]
            }
        }

        response = requests.post(_get_webhook_url(), json=payload)
        result = response.json()

        if result.get("code") == 0:
            return "✅ 新闻卡片发送成功"
        else:
            return f"❌ 新闻卡片发送失败: {result.get('msg', '未知错误')}"

    except Exception as e:
        return f"❌ 发送失败: {str(e)}"


@tool
def send_daily_news(ai_news: str, auto_news: str, tech_news: str = "") -> str:
    """
    发送完整的每日新闻推送，合并为一条消息。

    Args:
        ai_news: AI领域新闻内容
        auto_news: 自动驾驶新闻内容
        tech_news: 科技行业动态（已整合到AI新闻中）

    Returns:
        发送结果
    """
    try:
        # 构建完整消息
        full_message = _build_daily_news_message(ai_news, auto_news)

        # 发送一条完整的消息
        result = _send_text_impl(full_message)

        return result

    except Exception as e:
        return f"❌ 推送失败: {str(e)}"


def send_daily_news_func(ai_news: str, auto_news: str) -> str:
    """用于直接调用的非装饰函数"""
    return send_daily_news.invoke({"ai_news": ai_news, "auto_news": auto_news, "tech_news": ""})
