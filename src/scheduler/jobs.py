from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload

from src.config import get_settings
from src.crawlers.banks import CtbcCrawler
from src.models import CreditCard, Promotion
from src.models.notification_log import NotificationType
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.formatter import (
    format_expiring_promotions,
    format_new_cards,
    format_new_promotions,
)

settings = get_settings()

# 同步版本的資料庫連線（給排程使用）
sync_database_url = settings.database_url.replace("+aiosqlite", "")


def get_sync_session() -> Session:
    engine = create_engine(sync_database_url)
    return Session(engine)


def run_daily_promotion_crawl():
    """每日優惠爬取任務"""
    logger.info(f"Starting daily promotion crawl at {datetime.now()}")

    with get_sync_session() as session:
        crawlers = [
            CtbcCrawler(session),
            # 之後加入更多銀行爬蟲
        ]

        for crawler in crawlers:
            try:
                result = crawler.run()
                logger.info(f"Completed: {result}")
            except Exception as e:
                logger.error(f"Error crawling {crawler.bank_name}: {e}")

    logger.info("Daily promotion crawl completed")


def run_weekly_card_crawl():
    """每週信用卡資訊爬取任務"""
    logger.info(f"Starting weekly card crawl at {datetime.now()}")

    with get_sync_session() as session:
        crawlers = [
            CtbcCrawler(session),
        ]

        new_card_ids = []
        for crawler in crawlers:
            try:
                cards = crawler.fetch_cards()
                logger.info(f"Fetched {len(cards)} cards from {crawler.bank_name}")
                new_card_ids.extend(card.id for card in cards)
            except Exception as e:
                logger.error(f"Error crawling {crawler.bank_name}: {e}")

        # Notify about new cards
        if new_card_ids:
            try:
                _notify_new_cards(session, new_card_ids)
            except Exception as e:
                logger.error(f"Error sending new card notifications: {e}")

    logger.info("Weekly card crawl completed")


def cleanup_expired_promotions():
    """清理過期優惠"""
    logger.info("Cleaning up expired promotions")

    with get_sync_session() as session:
        today = datetime.now().date()
        expired = session.query(Promotion).filter(Promotion.end_date < today).all()

        for promo in expired:
            session.delete(promo)

        session.commit()
        logger.info(f"Deleted {len(expired)} expired promotions")


def check_new_promotions():
    """檢查今日新增優惠並發送通知"""
    logger.info("Checking for new promotions to notify")

    with get_sync_session() as session:
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        new_promos = (
            session.query(Promotion)
            .options(joinedload(Promotion.card).joinedload(CreditCard.bank))
            .filter(
                Promotion.created_at >= today_start,
                Promotion.created_at <= today_end,
            )
            .all()
        )

        if not new_promos:
            logger.info("No new promotions found today")
            return

        logger.info(f"Found {len(new_promos)} new promotions today")

        message = format_new_promotions(new_promos)
        reference_ids = [promo.id for promo in new_promos]

        dispatcher = NotificationDispatcher(session)
        results = dispatcher.dispatch(
            NotificationType.new_promotion, reference_ids, message
        )
        logger.info(f"New promotion notification results: {results}")


def check_expiring_promotions():
    """檢查即將到期優惠（3天內）並發送通知"""
    logger.info("Checking for expiring promotions to notify")

    with get_sync_session() as session:
        today = datetime.now().date()
        expiry_threshold = today + timedelta(days=3)

        expiring_promos = (
            session.query(Promotion)
            .options(joinedload(Promotion.card).joinedload(CreditCard.bank))
            .filter(
                Promotion.end_date >= today,
                Promotion.end_date <= expiry_threshold,
            )
            .all()
        )

        if not expiring_promos:
            logger.info("No expiring promotions in the next 3 days")
            return

        logger.info(f"Found {len(expiring_promos)} promotions expiring within 3 days")

        message = format_expiring_promotions(expiring_promos)
        reference_ids = [promo.id for promo in expiring_promos]

        dispatcher = NotificationDispatcher(session)
        results = dispatcher.dispatch(
            NotificationType.expiring_promotion, reference_ids, message
        )
        logger.info(f"Expiring promotion notification results: {results}")


def _notify_new_cards(session: Session, card_ids: List[int]):
    """發送新信用卡通知（由 run_weekly_card_crawl 呼叫）"""
    cards = (
        session.query(CreditCard)
        .options(joinedload(CreditCard.bank))
        .filter(CreditCard.id.in_(card_ids))
        .all()
    )

    if not cards:
        return

    message = format_new_cards(cards)
    reference_ids = [card.id for card in cards]

    dispatcher = NotificationDispatcher(session)
    results = dispatcher.dispatch(
        NotificationType.new_card, reference_ids, message
    )
    logger.info(f"New card notification results: {results}")
