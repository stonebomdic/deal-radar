from dataclasses import dataclass
from typing import Dict, List

from src.models import CreditCard, Promotion


@dataclass
class ScoringWeights:
    reward: float = 0.40
    feature: float = 0.25
    promotion: float = 0.15
    annual_fee_roi: float = 0.20


def estimate_monthly_reward(
    card: CreditCard,
    spending_habits: Dict[str, float],
    monthly_amount: int,
    promotions: List[Promotion],
    apply_limits: bool = True,
) -> float:
    """估算每月回饋金額（共用 helper）

    遍歷每個消費類別，找最佳回饋率及其上限，計算回饋並依需求套用上限。
    """
    total_reward = 0.0
    base_rate = card.base_reward_rate or 0.0

    for category, ratio in spending_habits.items():
        category_spend = monthly_amount * ratio

        best_rate = base_rate
        best_limit = None
        for promo in promotions:
            if promo.category == category and promo.reward_rate:
                if promo.reward_rate > best_rate:
                    best_rate = promo.reward_rate
                    best_limit = promo.reward_limit

        category_reward = category_spend * (best_rate / 100)

        if apply_limits and best_limit is not None and category_reward > best_limit:
            category_reward = best_limit

        total_reward += category_reward

    return total_reward


def calculate_reward_score(
    card: CreditCard,
    spending_habits: Dict[str, float],
    monthly_amount: int,
    promotions: List[Promotion],
) -> float:
    """計算回饋分數"""
    total_reward = estimate_monthly_reward(
        card, spending_habits, monthly_amount, promotions, apply_limits=True
    )

    # 正規化到 0-100
    max_possible = monthly_amount * 0.05  # 假設最高 5% 回饋
    score = min((total_reward / max_possible) * 100, 100) if max_possible > 0 else 0

    return round(score, 2)


def calculate_feature_score(
    card: CreditCard,
    preferences: List[str],
) -> float:
    """計算權益分數"""
    if not preferences:
        return 50.0

    features = card.features or {}
    matched = 0

    preference_mapping = {
        "no_annual_fee": lambda c: c.annual_fee == 0 or c.annual_fee is None,
        "airport_pickup": lambda c: features.get("airport_pickup", False),
        "lounge_access": lambda c: (
            features.get("lounge_access") or features.get("lounge", False)
        ),
        "cashback": lambda c: features.get("reward_type") == "cashback",
        "miles": lambda c: features.get("reward_type") == "miles",
        "high_reward": lambda c: (c.base_reward_rate or 0) >= 2.0,
        "travel": lambda c: (
            features.get("reward_type") == "miles"
            or features.get("overseas", False)
            or features.get("airport_transfer", False)
        ),
        "dining": lambda c: features.get("dining", False),
        "mobile_pay": lambda c: features.get("mobile_pay", False),
        "online_shopping": lambda c: features.get("online_shopping", False),
        "new_cardholder": lambda c: features.get("new_cardholder_bonus", False),
        "installment": lambda c: features.get("installment", False),
        "streaming": lambda c: features.get("streaming", False),
        "travel_insurance": lambda c: features.get("travel_insurance", False),
    }

    for pref in preferences:
        if pref in preference_mapping:
            if preference_mapping[pref](card):
                matched += 1

    score = (matched / len(preferences)) * 100
    return round(score, 2)


def calculate_annual_fee_roi(
    card: CreditCard,
    monthly_amount: int,
    spending_habits: Dict[str, float],
    promotions: List[Promotion],
) -> float:
    """計算年費投資報酬率分數

    Free cards get 80. For paid cards, estimate annual reward vs annual fee.
    ROI = (annual_reward - annual_fee) / annual_spending
    Score is normalized to 0-100.
    """
    annual_fee = card.annual_fee or 0
    if annual_fee == 0:
        return 80.0

    monthly_reward = estimate_monthly_reward(
        card, spending_habits, monthly_amount, promotions, apply_limits=True
    )

    annual_reward = monthly_reward * 12
    annual_spending = monthly_amount * 12

    if annual_spending == 0:
        return 0.0

    roi = (annual_reward - annual_fee) / annual_spending * 100

    if roi <= 0:
        return 0.0

    # Normalize: 5% net ROI = perfect score
    score = min(roi / 0.05, 100)
    return round(score, 2)


def calculate_promotion_score(promotions: List[Promotion]) -> float:
    """計算優惠分數

    Weights each promotion by its reward_rate (capped at 10).
    Promos without a rate contribute 1 point.
    Formula: score = min(sum(min(rate or 1, 10) for each promo) * 5, 100)
    """
    if not promotions:
        return 0.0

    total = sum(min(promo.reward_rate or 1, 10) for promo in promotions)
    score = min(total * 5, 100)
    return round(score, 2)


def calculate_total_score(
    card: CreditCard,
    spending_habits: Dict[str, float],
    monthly_amount: int,
    preferences: List[str],
    promotions: List[Promotion],
    weights: ScoringWeights = None,
) -> Dict:
    """計算總分"""
    if weights is None:
        weights = ScoringWeights()

    reward_score = calculate_reward_score(card, spending_habits, monthly_amount, promotions)
    feature_score = calculate_feature_score(card, preferences)
    promotion_score = calculate_promotion_score(promotions)
    roi_score = calculate_annual_fee_roi(card, monthly_amount, spending_habits, promotions)

    total = (
        reward_score * weights.reward
        + feature_score * weights.feature
        + promotion_score * weights.promotion
        + roi_score * weights.annual_fee_roi
    )

    return {
        "total": round(total, 2),
        "reward_score": reward_score,
        "feature_score": feature_score,
        "promotion_score": promotion_score,
        "annual_fee_roi_score": roi_score,
    }


def calculate_shopping_reward(
    card: CreditCard,
    platform: str,
    amount: int,
    promotions: List[Promotion],
) -> Dict:
    """計算單次購物的最佳回饋

    Args:
        card: 信用卡
        platform: "pchome" 或 "momo"
        amount: 購物金額（元）
        promotions: 該卡目前有效的優惠列表

    Returns:
        {"reward_amount": float, "best_rate": float, "reason": str}
    """
    platform_category = {"pchome": "online_shopping", "momo": "online_shopping"}
    category = platform_category.get(platform, "online_shopping")

    base_rate = card.base_reward_rate or 0.0
    best_rate = base_rate
    best_limit = None

    for promo in promotions:
        if promo.category == category and promo.reward_rate:
            if promo.reward_rate > best_rate:
                best_rate = promo.reward_rate
                best_limit = promo.reward_limit

    reward = amount * (best_rate / 100)
    if best_limit is not None and reward > best_limit:
        reward = float(best_limit)

    reason = f"{platform.upper()} 回饋 {best_rate}%"
    if best_limit:
        reason += f"（上限 {best_limit} 元）"

    return {
        "reward_amount": round(reward, 2),
        "best_rate": best_rate,
        "reason": reason,
    }
