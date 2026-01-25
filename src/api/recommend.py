from typing import Dict, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import get_settings
from src.db.database import get_db
from src.recommender.engine import RecommendationEngine, RecommendRequest

router = APIRouter(prefix="/api", tags=["recommend"])

# 為推薦引擎創建同步 session
settings = get_settings()
sync_db_url = settings.database_url.replace("+aiosqlite", "")
sync_engine = create_engine(sync_db_url)
SyncSession = sessionmaker(bind=sync_engine)


class RecommendRequestSchema(BaseModel):
    spending_habits: Dict[str, float]
    monthly_amount: int
    preferences: List[str] = []
    limit: int = 5


class CardRecommendationSchema(BaseModel):
    rank: int
    card_id: int
    card_name: str
    bank_name: str
    score: float
    estimated_monthly_reward: float
    reasons: List[str]


class RecommendResponseSchema(BaseModel):
    recommendations: List[CardRecommendationSchema]


@router.post("/recommend", response_model=RecommendResponseSchema)
async def get_recommendations(
    request: RecommendRequestSchema,
    db: AsyncSession = Depends(get_db),
):
    # 使用同步 session 執行推薦引擎
    with SyncSession() as sync_session:
        engine = RecommendationEngine(sync_session)
        recommend_request = RecommendRequest(
            spending_habits=request.spending_habits,
            monthly_amount=request.monthly_amount,
            preferences=request.preferences,
            limit=request.limit,
        )
        results = engine.recommend(recommend_request)

        recommendations = []
        for rank, rec in enumerate(results, start=1):
            recommendations.append(
                CardRecommendationSchema(
                    rank=rank,
                    card_id=rec.card.id,
                    card_name=rec.card.name,
                    bank_name=rec.card.bank.name,
                    score=round(rec.score, 2),
                    estimated_monthly_reward=rec.estimated_monthly_reward,
                    reasons=rec.reasons,
                )
            )

        return RecommendResponseSchema(recommendations=recommendations)
