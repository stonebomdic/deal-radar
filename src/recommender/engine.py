from dataclasses import dataclass
from typing import Dict, List

from sqlalchemy.orm import Session

from src.models import CreditCard, Promotion
from src.recommender.scoring import calculate_total_score


@dataclass
class RecommendRequest:
    spending_habits: Dict[str, float]
    monthly_amount: int
    preferences: List[str]
    limit: int = 5


@dataclass
class CardRecommendation:
    card: CreditCard
    score: float
    reward_score: float
    feature_score: float
    promotion_score: float
    annual_fee_roi_score: float
    estimated_monthly_reward: float
    reasons: List[str]


class RecommendationEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def recommend(self, request: RecommendRequest) -> List[CardRecommendation]:
        # 取得所有信用卡
        cards = self.db.query(CreditCard).all()

        # 篩選
        filtered_cards = self._filter_cards(cards, request)

        # 評分
        scored_cards = []
        for card in filtered_cards:
            promotions = self.db.query(Promotion).filter_by(card_id=card.id).all()

            scores = calculate_total_score(
                card=card,
                spending_habits=request.spending_habits,
                monthly_amount=request.monthly_amount,
                preferences=request.preferences,
                promotions=promotions,
            )

            estimated_reward = self._estimate_monthly_reward(
                card, request.spending_habits, request.monthly_amount, promotions
            )

            reasons = self._generate_reasons(card, request, scores, promotions)

            scored_cards.append(
                CardRecommendation(
                    card=card,
                    score=scores["total"],
                    reward_score=scores["reward_score"],
                    feature_score=scores["feature_score"],
                    promotion_score=scores["promotion_score"],
                    annual_fee_roi_score=scores["annual_fee_roi_score"],
                    estimated_monthly_reward=estimated_reward,
                    reasons=reasons,
                )
            )

        # 排序並返回 Top N
        scored_cards.sort(key=lambda x: x.score, reverse=True)
        return scored_cards[: request.limit]

    def _filter_cards(
        self, cards: List[CreditCard], request: RecommendRequest
    ) -> List[CreditCard]:
        """篩選符合條件的信用卡"""
        filtered = []

        for card in cards:
            # 如果要求免年費，過濾掉有年費的卡
            if "no_annual_fee" in request.preferences:
                if card.annual_fee and card.annual_fee > 0:
                    continue
            filtered.append(card)

        return filtered

    def _estimate_monthly_reward(
        self,
        card: CreditCard,
        spending_habits: Dict[str, float],
        monthly_amount: int,
        promotions: List[Promotion],
    ) -> float:
        """估算每月回饋金額"""
        total_reward = 0.0
        base_rate = card.base_reward_rate or 0.0

        for category, ratio in spending_habits.items():
            category_spend = monthly_amount * ratio

            best_rate = base_rate
            for promo in promotions:
                if promo.category == category and promo.reward_rate:
                    if promo.reward_rate > best_rate:
                        best_rate = promo.reward_rate

            total_reward += category_spend * (best_rate / 100)

        return round(total_reward, 0)

    def _generate_reasons(
        self,
        card: CreditCard,
        request: RecommendRequest,
        scores: Dict,
        promotions: List[Promotion],
    ) -> List[str]:
        """產生推薦理由"""
        reasons = []

        category_names = {
            "dining": "餐飲",
            "online_shopping": "網購",
            "transport": "交通",
            "overseas": "海外",
            "convenience_store": "超商",
            "department_store": "百貨",
            "travel": "旅遊",
            "mobile_pay": "行動支付",
            "supermarket": "超市",
            "insurance": "保險",
            "education": "教育",
            "medical": "醫療",
            "others": "一般",
        }

        # 回饋相關
        if scores["reward_score"] > 70:
            top_category = max(
                request.spending_habits, key=request.spending_habits.get
            )
            cat_name = category_names.get(top_category, top_category)
            reasons.append(f"{cat_name}回饋符合您的消費習慣")

        # 高回饋優惠活動明細
        for promo in promotions:
            if promo.reward_rate and promo.reward_rate >= 3.0 and promo.category:
                cat_name = category_names.get(promo.category, promo.category)
                rate_str = f"{promo.reward_rate:g}"
                reasons.append(f"{cat_name}類消費最高 {rate_str}% 回饋")

        # 年費相關
        if card.annual_fee == 0 or card.annual_fee is None:
            reasons.append("免年費")
        elif scores.get("annual_fee_roi_score", 0) > 60:
            annual_fee = card.annual_fee or 0
            if annual_fee > 0:
                base_rate = card.base_reward_rate or 0.0
                monthly_reward = 0.0
                for category, ratio in request.spending_habits.items():
                    category_spend = request.monthly_amount * ratio
                    best_rate = base_rate
                    for promo in promotions:
                        if promo.category == category and promo.reward_rate:
                            if promo.reward_rate > best_rate:
                                best_rate = promo.reward_rate
                    monthly_reward += category_spend * (best_rate / 100)
                annual_reward = monthly_reward * 12
                multiplier = annual_reward / annual_fee if annual_fee > 0 else 0
                if multiplier >= 1:
                    reasons.append(
                        f"年回饋預估超過年費 {multiplier:.1f} 倍"
                    )

        # 回饋上限提醒
        has_limit = any(
            promo.reward_limit is not None and promo.reward_limit > 0
            for promo in promotions
        )
        if has_limit:
            reasons.append("注意：部分回饋有每月上限")

        # 優惠數量
        if promotions and len(reasons) < 4:
            reasons.append(f"目前有 {len(promotions)} 個優惠活動")

        return reasons[:5]  # 最多 5 個理由
