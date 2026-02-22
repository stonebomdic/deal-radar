from fastapi import APIRouter

from src.api.cards import router as cards_router
from src.api.products import router as products_router
from src.api.recommend import router as recommend_router

api_router = APIRouter()
api_router.include_router(cards_router)
api_router.include_router(recommend_router)
api_router.include_router(products_router)
