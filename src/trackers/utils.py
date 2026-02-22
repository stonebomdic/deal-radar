from __future__ import annotations

from typing import Optional, Tuple

from loguru import logger
from sqlalchemy.orm import Session

from src.models.flash_deal import FlashDeal
from src.models.notification_log import NotificationType
from src.models.price_history import PriceHistory
from src.models.tracked_product import TrackedProduct
from src.notifications.dispatcher import NotificationDispatcher
from src.notifications.formatter import format_price_drop_alert
from src.trackers.base import BaseTracker


def get_tracker(platform: str) -> Optional[BaseTracker]:
    """根據 platform 名稱取得對應 Tracker 實例"""
    if platform == "pchome":
        from src.trackers.platforms.pchome import PChomeTracker

        return PChomeTracker()
    elif platform == "momo":
        from src.trackers.platforms.momo import MomoTracker

        return MomoTracker()
    logger.warning(f"Unknown platform: {platform}")
    return None


def check_price_and_snapshot(
    session: Session, product: TrackedProduct
) -> Tuple[Optional[PriceHistory], bool, bool]:
    """
    爬取最新價格並存入 price_history。

    Returns:
        (new_snapshot, is_price_drop, is_target_reached)
    """
    tracker = get_tracker(product.platform)
    if tracker is None:
        return None, False, False

    snapshot = tracker.fetch_price(product.product_id)
    if snapshot is None:
        logger.warning(f"No price fetched for product {product.id}")
        return None, False, False

    last = (
        session.query(PriceHistory)
        .filter_by(product_id=product.id)
        .order_by(PriceHistory.snapshot_at.desc())
        .first()
    )

    new_record = PriceHistory(
        product_id=product.id,
        price=snapshot.price,
        original_price=snapshot.original_price,
        in_stock=snapshot.in_stock,
        source="price_check",
    )
    session.add(new_record)
    session.commit()
    session.refresh(new_record)

    is_price_drop = last is not None and snapshot.price < last.price
    is_target_reached = (
        product.target_price is not None and snapshot.price <= product.target_price
    )

    return new_record, is_price_drop, is_target_reached


def refresh_flash_deals(session: Session, platform: str) -> int:
    """爬取並更新 flash_deals 資料表，回傳新增筆數。
    若新加入的特賣商品與追蹤清單有 URL 匹配，建立 PriceHistory 並視情況發送通知。
    """
    tracker = get_tracker(platform)
    if tracker is None:
        return 0

    deals = tracker.fetch_flash_deals()
    count = 0
    for deal in deals:
        existing = (
            session.query(FlashDeal)
            .filter_by(platform=deal.platform, product_url=deal.product_url)
            .first()
        )
        if existing is not None:
            continue

        record = FlashDeal(
            platform=deal.platform,
            product_name=deal.product_name,
            product_url=deal.product_url,
            sale_price=deal.sale_price,
            original_price=deal.original_price,
            discount_rate=deal.discount_rate,
        )
        session.add(record)
        count += 1

        # 比對追蹤清單
        matched = (
            session.query(TrackedProduct)
            .filter_by(url=deal.product_url, is_active=True)
            .first()
        )
        if matched is None:
            continue

        last = (
            session.query(PriceHistory)
            .filter_by(product_id=matched.id)
            .order_by(PriceHistory.snapshot_at.desc())
            .first()
        )

        snapshot = PriceHistory(
            product_id=matched.id,
            price=deal.sale_price,
            original_price=deal.original_price,
            in_stock=True,
            source="flash_deal",
        )
        session.add(snapshot)
        session.flush()

        if last is not None and deal.sale_price < last.price:
            message = format_price_drop_alert(matched, snapshot, [], False)
            dispatcher = NotificationDispatcher(session)
            dispatcher.dispatch(NotificationType.price_drop, [snapshot.id], message)

    session.commit()
    return count
