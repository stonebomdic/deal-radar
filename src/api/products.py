from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.models.flash_deal import FlashDeal
from src.models.price_history import PriceHistory
from src.models.tracked_product import TrackedProduct

router = APIRouter(prefix="/api", tags=["products"])


class AddProductRequest(BaseModel):
    platform: str
    url: Optional[str] = None
    keyword: Optional[str] = None
    target_price: Optional[int] = None


class ProductResponse(BaseModel):
    id: int
    platform: str
    name: str
    url: str
    target_price: Optional[int]
    is_active: bool
    current_price: Optional[int] = None
    lowest_price: Optional[int] = None


class PriceHistoryResponse(BaseModel):
    price: int
    original_price: Optional[int]
    in_stock: bool
    snapshot_at: str


@router.get("/products")
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackedProduct).where(TrackedProduct.is_active == True))  # noqa: E712
    products = result.scalars().all()
    return {
        "items": [
            ProductResponse(
                id=p.id,
                platform=p.platform,
                name=p.name,
                url=p.url,
                target_price=p.target_price,
                is_active=p.is_active,
            )
            for p in products
        ]
    }


@router.post("/products", status_code=201)
async def add_product(body: AddProductRequest, db: AsyncSession = Depends(get_db)):
    if not body.url and not body.keyword:
        raise HTTPException(status_code=400, detail="url 或 keyword 至少提供一個")

    platform = body.platform.lower()
    if platform not in ("pchome", "momo"):
        raise HTTPException(status_code=400, detail="platform 僅支援 pchome 或 momo")

    if body.url:
        existing = await db.execute(
            select(TrackedProduct).where(TrackedProduct.url == body.url)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="此商品已在追蹤清單中")

        url = body.url
        if platform == "pchome":
            pid = url.rstrip("/").split("/")[-1]
        else:
            m = re.search(r"i_code=(\d+)", url)
            pid = m.group(1) if m else url

        product = TrackedProduct(
            platform=platform,
            product_id=pid,
            name=pid,
            url=url,
            target_price=body.target_price,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return {"id": product.id, "message": "已加入追蹤"}

    from src.trackers.utils import get_tracker

    tracker = get_tracker(platform)
    if tracker is None:
        raise HTTPException(status_code=500, detail="Tracker 不可用")
    results = tracker.search_products(body.keyword)
    return {
        "results": [
            {
                "platform": r.platform,
                "product_id": r.product_id,
                "name": r.name,
                "url": r.url,
                "price": r.price,
            }
            for r in results
        ]
    }


@router.delete("/products/{product_id}", status_code=204)
async def remove_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TrackedProduct).where(TrackedProduct.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    product.is_active = False
    await db.commit()


@router.get("/products/{product_id}/history")
async def get_price_history(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.snapshot_at.asc())
    )
    history = result.scalars().all()
    return [
        PriceHistoryResponse(
            price=h.price,
            original_price=h.original_price,
            in_stock=h.in_stock,
            snapshot_at=h.snapshot_at.isoformat(),
        )
        for h in history
    ]


@router.get("/flash-deals")
async def list_flash_deals(
    platform: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(FlashDeal).order_by(FlashDeal.discount_rate.asc())
    if platform:
        stmt = stmt.where(FlashDeal.platform == platform)
    result = await db.execute(stmt)
    deals = result.scalars().all()
    return [
        {
            "id": d.id,
            "platform": d.platform,
            "product_name": d.product_name,
            "product_url": d.product_url,
            "sale_price": d.sale_price,
            "original_price": d.original_price,
            "discount_rate": d.discount_rate,
        }
        for d in deals
    ]
