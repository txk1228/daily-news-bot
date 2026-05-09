"""
每日新闻推送机器人 Agent

角色：科技新闻助手，专注于AI和自动驾驶领域的最新动态
功能：
1. 搜索最新AI新闻（3条）
2. 搜索自动驾驶新闻（3条）
3. 合并推送一条消息到飞书群
"""
import os
import json
from typing import Annotated
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver
from tools.news_search_tool import search_ai_news, search_autonomous_driving_news
from tools.feishu_message_tool import send_daily_news
from tools.scheduler import start_scheduler

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40

def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore

class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]

def build_agent(ctx=None):
    """
    构建每日新闻推送 Agent

    整合以下能力：
    1. AI新闻搜索（3条）
    2. 自动驾驶新闻搜索（3条）
    3. 合并推送一条消息到飞书
    """
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        default_headers=default_headers(ctx) if ctx else {}
    )

    tools = [
        search_ai_news,
        search_autonomous_driving_news,
        send_daily_news
    ]

    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=tools,
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )

def initialize():
    """
    初始化 Agent 和定时任务调度器
    """
    start_scheduler()
