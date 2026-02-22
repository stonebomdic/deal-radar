from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.scheduler.jobs import (
    check_expiring_promotions,
    check_new_promotions,
    cleanup_expired_promotions,
    run_daily_promotion_crawl,
    run_flash_deals_refresh,
    run_price_tracking,
    run_weekly_card_crawl,
)


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()

    # 每日凌晨 2:00 執行優惠爬取
    scheduler.add_job(
        run_daily_promotion_crawl,
        CronTrigger(hour=2, minute=0),
        id="daily_promotion_crawl",
        name="Daily Promotion Crawl",
    )

    # 每週日凌晨 3:00 執行信用卡資訊爬取
    scheduler.add_job(
        run_weekly_card_crawl,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="weekly_card_crawl",
        name="Weekly Card Crawl",
    )

    # 每日凌晨 4:00 清理過期優惠
    scheduler.add_job(
        cleanup_expired_promotions,
        CronTrigger(hour=4, minute=0),
        id="cleanup_expired",
        name="Cleanup Expired Promotions",
    )

    # 每日 06:00 檢查新優惠並通知（在爬蟲之後）
    scheduler.add_job(
        check_new_promotions,
        CronTrigger(hour=6, minute=0),
        id="check_new_promotions",
        name="Check New Promotions",
    )

    # 每日 09:00 檢查即將到期優惠並通知
    scheduler.add_job(
        check_expiring_promotions,
        CronTrigger(hour=9, minute=0),
        id="check_expiring_promotions",
        name="Check Expiring Promotions",
    )

    # 每 30 分鐘追蹤商品價格
    scheduler.add_job(
        run_price_tracking,
        "interval",
        minutes=30,
        id="price_tracking",
        name="Price Tracking",
    )

    # 每 1 小時更新限時瘋搶
    scheduler.add_job(
        run_flash_deals_refresh,
        "interval",
        hours=1,
        id="flash_deals_refresh",
        name="Flash Deals Refresh",
    )

    logger.info("Scheduler configured with jobs")
    return scheduler


def start_scheduler():
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Scheduler started")
    return scheduler
