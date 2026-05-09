#!/usr/bin/env python3
"""
每日新闻推送定时调度器
每天 08:30 自动执行新闻推送
"""
import sys
import os
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/news_scheduler.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def job_news_push():
    """执行新闻推送任务"""
    logger.info("=" * 60)
    logger.info(f"定时任务触发 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # 添加项目路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        
        # 导入并执行推送
        from scripts.news_bot import job_news_push as execute
        execute()
        
        logger.info(f"任务完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logger.error(f"推送失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数 - 设置定时任务"""
    logger.info("=" * 60)
    logger.info("📅 每日新闻推送调度器启动")
    logger.info("⏰ 推送时间: 每天 08:30 (北京时间)")
    logger.info("=" * 60)
    
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from pytz import timezone
        
        # 创建调度器
        scheduler = BlockingScheduler(timezone=timezone('Asia/Shanghai'))
        
        # 添加定时任务: 每天 08:30
        scheduler.add_job(
            job_news_push,
            CronTrigger(hour=8, minute=30, timezone='Asia/Shanghai'),
            id='daily_news_push',
            name='每日新闻推送',
            replace_existing=True
        )
        
        logger.info("✅ 定时任务已设置")
        logger.info("📡 等待执行...")
        
        # 立即执行一次（可选）
        logger.info("🚀 立即执行首次推送...")
        job_news_push()
        
        # 启动调度器
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("调度器已停止")
    except Exception as e:
        logger.error(f"调度器启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
