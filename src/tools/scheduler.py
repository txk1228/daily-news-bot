"""
定时任务调度器 - 每日北京时间早上8点推送新闻
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

logger = logging.getLogger(__name__)

# 全局调度器实例
_scheduler = None


def daily_news_job():
    """
    每日新闻推送任务 - 由调度器触发
    这个函数会在北京时间每天早上8点被调用
    """
    try:
        logger.info("触发每日新闻推送任务...")

        # 动态导入以避免循环导入
        from news_push_executor import execute_daily_news_push

        # 执行新闻推送
        result = execute_daily_news_push()
        logger.info(f"每日新闻推送完成: {result}")

    except Exception as e:
        logger.error(f"每日新闻推送失败: {str(e)}", exc_info=True)


def start_scheduler():
    """
    启动定时任务调度器
    设置北京时间每天早上8点执行新闻推送
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("⏰ 调度器已在运行中")
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # 设置 cron 触发器：北京时间每天早上7:30
    trigger = CronTrigger(
        hour=7,           # 早上7点
        minute=30,        # 30分
        timezone="Asia/Shanghai"
    )

    _scheduler.add_job(
        daily_news_job,
        trigger=trigger,
        id="daily_news_push",
        name="每日科技新闻推送",
        replace_existing=True,
        misfire_grace_time=3600  # 允许1小时的误差
    )

    _scheduler.start()
    logger.info("定时任务调度器已启动 - 每日北京时间07:30执行新闻推送")


def stop_scheduler():
    """停止定时任务调度器"""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("⏰ 定时任务调度器已停止")


def get_scheduler_status():
    """获取调度器状态"""
    if _scheduler is None:
        return {"status": "未初始化"}

    if not _scheduler.running:
        return {"status": "已停止"}

    jobs = _scheduler.get_jobs()
    return {
        "status": "运行中",
        "jobs_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }


def trigger_news_push_now():
    """
    手动触发一次新闻推送（用于测试）
    """
    logger.info("🔧 手动触发新闻推送...")
    daily_news_job()
    return "✅ 手动触发成功"
