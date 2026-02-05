import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models import Bank, CreditCard, Promotion
from src.recommender.engine import RecommendationEngine, RecommendRequest
from src.recommender.scoring import (
    ScoringWeights,
    calculate_annual_fee_roi,
    calculate_feature_score,
    calculate_promotion_score,
    calculate_reward_score,
    calculate_total_score,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # Add test data
        bank = Bank(name="測試銀行", code="test")
        session.add(bank)
        session.commit()

        card1 = CreditCard(
            bank_id=bank.id,
            name="高回饋卡",
            annual_fee=0,
            base_reward_rate=2.0,
        )
        card2 = CreditCard(
            bank_id=bank.id,
            name="年費卡",
            annual_fee=2000,
            base_reward_rate=3.0,
        )
        session.add_all([card1, card2])
        session.commit()

        promo = Promotion(
            card_id=card1.id,
            title="網購優惠",
            category="online_shopping",
            reward_rate=5.0,
        )
        session.add(promo)
        session.commit()

        yield session
    Base.metadata.drop_all(engine)


def test_calculate_feature_score_no_annual_fee():
    card = CreditCard(name="測試", annual_fee=0)
    score = calculate_feature_score(card, ["no_annual_fee"])
    assert score == 100.0


def test_calculate_feature_score_with_annual_fee():
    card = CreditCard(name="測試", annual_fee=2000)
    score = calculate_feature_score(card, ["no_annual_fee"])
    assert score == 0.0


def test_calculate_promotion_score():
    promos = [Promotion(title="優惠1"), Promotion(title="優惠2")]
    score = calculate_promotion_score(promos)
    assert score == 10.0  # Each promo without rate contributes 1, total = (1+1)*5 = 10


def test_annual_fee_roi_free_card():
    """Free cards should get a score of 80."""
    card = CreditCard(name="Free Card", annual_fee=0, base_reward_rate=1.0)
    score = calculate_annual_fee_roi(
        card=card,
        monthly_amount=30000,
        spending_habits={"dining": 0.5, "others": 0.5},
        promotions=[],
    )
    assert score == 80.0


def test_annual_fee_roi_none_fee_card():
    """Cards with annual_fee=None should also get 80."""
    card = CreditCard(name="No Fee Info", annual_fee=None, base_reward_rate=1.0)
    score = calculate_annual_fee_roi(
        card=card,
        monthly_amount=30000,
        spending_habits={"dining": 0.5, "others": 0.5},
        promotions=[],
    )
    assert score == 80.0


def test_annual_fee_roi_high_reward_covers_fee():
    """Card with 3% base rate, 2000 annual fee, spending 50000/month."""
    card = CreditCard(name="Premium Card", annual_fee=2000, base_reward_rate=3.0)
    score = calculate_annual_fee_roi(
        card=card,
        monthly_amount=50000,
        spending_habits={"dining": 1.0},
        promotions=[],
    )
    # ROI = (1500*12 - 2000) / (50000*12) * 100 = 16000/600000 * 100 = 2.667
    # score = min(2.667 / 0.05 * 100, 100) = min(53.33, 100) = 53.33
    assert score == 53.33


def test_annual_fee_roi_fee_exceeds_reward():
    """Card where annual fee exceeds annual reward should score 0."""
    card = CreditCard(name="Expensive Card", annual_fee=5000, base_reward_rate=0.5)
    score = calculate_annual_fee_roi(
        card=card,
        monthly_amount=10000,
        spending_habits={"others": 1.0},
        promotions=[],
    )
    # Monthly reward = 10000 * 0.5% = 50, annual = 600
    # ROI = (600 - 5000) / 120000 * 100 = -3.67
    # Negative => score = 0
    assert score == 0.0


def test_annual_fee_roi_with_promotion():
    """Promotions should boost the estimated reward used in ROI calculation."""
    card = CreditCard(name="Promo Card", annual_fee=1000, base_reward_rate=1.0)
    promo = Promotion(title="Dining Promo", category="dining", reward_rate=5.0)
    score = calculate_annual_fee_roi(
        card=card,
        monthly_amount=20000,
        spending_habits={"dining": 0.5, "others": 0.5},
        promotions=[promo],
    )
    # dining: 10000 * 5% = 500, others: 10000 * 1% = 100 => monthly = 600
    # ROI = (600*12 - 1000) / (20000*12) * 100 = 6200/240000 * 100 = 2.583
    # score = min(2.583 / 0.05 * 100, 100) = min(51.67, 100) = 51.67
    assert score == 51.67


def test_reward_score_respects_reward_limit():
    """Card with 5% rate but 200 limit should cap reward at 200 for that category."""
    card = CreditCard(name="Limited Card", base_reward_rate=1.0)
    promo_limited = Promotion(
        title="High Rate Limited",
        category="dining",
        reward_rate=5.0,
        reward_limit=200,
    )
    score_limited = calculate_reward_score(
        card=card,
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        promotions=[promo_limited],
    )
    # Without limit: 30000 * 5% = 1500
    # With limit: min(1500, 200) = 200
    # max_possible = 30000 * 0.05 = 1500
    # score = (200 / 1500) * 100 = 13.33
    assert score_limited == 13.33


def test_reward_score_no_limit_vs_limited():
    """Card with 2% no limit should beat 5% with 200 limit when spending 30000."""
    card_a = CreditCard(name="No Limit Card", base_reward_rate=1.0)
    promo_no_limit = Promotion(
        title="Moderate No Limit",
        category="dining",
        reward_rate=2.0,
        reward_limit=None,
    )
    score_no_limit = calculate_reward_score(
        card=card_a,
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        promotions=[promo_no_limit],
    )

    card_b = CreditCard(name="Limited Card", base_reward_rate=1.0)
    promo_limited = Promotion(
        title="High Rate Limited",
        category="dining",
        reward_rate=5.0,
        reward_limit=200,
    )
    score_limited = calculate_reward_score(
        card=card_b,
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        promotions=[promo_limited],
    )

    # No limit: 30000 * 2% = 600 => score = (600/1500)*100 = 40.0
    # Limited: min(30000*5%, 200) = 200 => score = (200/1500)*100 = 13.33
    assert score_no_limit > score_limited


def test_reward_score_limit_not_reached():
    """When spending is low enough that limit isn't reached, reward is not capped."""
    card = CreditCard(name="Card", base_reward_rate=1.0)
    promo = Promotion(
        title="Limited Promo",
        category="dining",
        reward_rate=5.0,
        reward_limit=500,
    )
    score = calculate_reward_score(
        card=card,
        spending_habits={"dining": 1.0},
        monthly_amount=5000,
        promotions=[promo],
    )
    # 5000 * 5% = 250 < 500 limit, so no cap
    # max_possible = 5000 * 0.05 = 250
    # score = (250/250)*100 = 100.0
    assert score == 100.0


def test_feature_score_high_reward():
    """high_reward preference matches cards with base_reward_rate >= 2.0."""
    card_high = CreditCard(name="High", base_reward_rate=2.5)
    card_low = CreditCard(name="Low", base_reward_rate=1.0)
    assert calculate_feature_score(card_high, ["high_reward"]) == 100.0
    assert calculate_feature_score(card_low, ["high_reward"]) == 0.0


def test_feature_score_travel():
    """travel preference matches cards with mileage, overseas, or airport_transfer features."""
    card_miles = CreditCard(name="Miles Card", features={"reward_type": "miles"})
    card_overseas = CreditCard(name="Overseas Card", features={"overseas": True})
    card_airport = CreditCard(name="Airport Card", features={"airport_transfer": True})
    card_plain = CreditCard(name="Plain Card", features={"reward_type": "cashback"})

    assert calculate_feature_score(card_miles, ["travel"]) == 100.0
    assert calculate_feature_score(card_overseas, ["travel"]) == 100.0
    assert calculate_feature_score(card_airport, ["travel"]) == 100.0
    assert calculate_feature_score(card_plain, ["travel"]) == 0.0


def test_feature_score_dining():
    """dining preference matches cards with dining-related features."""
    card_dining = CreditCard(name="Dining Card", features={"dining": True})
    card_no_dining = CreditCard(name="Other Card", features={"online_shopping": True})
    assert calculate_feature_score(card_dining, ["dining"]) == 100.0
    assert calculate_feature_score(card_no_dining, ["dining"]) == 0.0


def test_feature_score_mobile_pay():
    """mobile_pay preference matches cards with mobile_pay feature."""
    card_mobile = CreditCard(name="Mobile Card", features={"mobile_pay": True})
    card_no_mobile = CreditCard(name="Other Card", features={})
    assert calculate_feature_score(card_mobile, ["mobile_pay"]) == 100.0
    assert calculate_feature_score(card_no_mobile, ["mobile_pay"]) == 0.0


def test_feature_score_online_shopping():
    """online_shopping preference matches cards with online_shopping feature."""
    card_online = CreditCard(name="Online Card", features={"online_shopping": True})
    card_no_online = CreditCard(name="Other Card", features={})
    assert calculate_feature_score(card_online, ["online_shopping"]) == 100.0
    assert calculate_feature_score(card_no_online, ["online_shopping"]) == 0.0


def test_feature_score_multiple_new_preferences():
    """Multiple new preferences should calculate correctly."""
    card = CreditCard(
        name="Super Card",
        annual_fee=0,
        base_reward_rate=3.0,
        features={"mobile_pay": True, "dining": True, "online_shopping": True},
    )
    # no_annual_fee (match), high_reward (match), dining (match), travel (no match)
    score = calculate_feature_score(card, ["no_annual_fee", "high_reward", "dining", "travel"])
    # 3 out of 4 matched = 75.0
    assert score == 75.0


def test_promotion_score_weights_by_rate():
    """One promo with 10% rate should score higher than three promos with 1% rate."""
    promo_high = [Promotion(title="High Rate", reward_rate=10.0)]
    promo_low = [
        Promotion(title="Low 1", reward_rate=1.0),
        Promotion(title="Low 2", reward_rate=1.0),
        Promotion(title="Low 3", reward_rate=1.0),
    ]

    score_high = calculate_promotion_score(promo_high)
    score_low = calculate_promotion_score(promo_low)

    # High: min(min(10, 10) * 5, 100) = min(50, 100) = 50
    # Low: min((1+1+1) * 5, 100) = min(15, 100) = 15
    assert score_high == 50.0
    assert score_low == 15.0
    assert score_high > score_low


def test_promotion_score_caps_individual_rate():
    """Individual promo rate contribution should be capped at 10."""
    promo = [Promotion(title="Extreme", reward_rate=20.0)]
    score = calculate_promotion_score(promo)
    # min(20, 10) = 10, then 10 * 5 = 50
    assert score == 50.0


def test_promotion_score_no_rate_defaults_to_one():
    """Promos without reward_rate should contribute 1."""
    promos = [
        Promotion(title="No Rate 1", reward_rate=None),
        Promotion(title="No Rate 2", reward_rate=None),
    ]
    score = calculate_promotion_score(promos)
    # (1 + 1) * 5 = 10
    assert score == 10.0


def test_promotion_score_caps_at_100():
    """Total score should be capped at 100."""
    promos = [Promotion(title=f"P{i}", reward_rate=10.0) for i in range(5)]
    score = calculate_promotion_score(promos)
    # 5 * min(10, 10) * 5 = 250, capped at 100
    assert score == 100.0


def test_total_score_includes_roi():
    """Total score should include annual_fee_roi component."""
    card = CreditCard(name="Test Card", annual_fee=0, base_reward_rate=2.0)
    scores = calculate_total_score(
        card=card,
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        preferences=["no_annual_fee"],
        promotions=[],
    )
    assert "annual_fee_roi_score" in scores
    assert scores["annual_fee_roi_score"] == 80.0  # Free card


def test_total_score_new_weights():
    """Total score should use new default weights."""
    card = CreditCard(name="Test", annual_fee=0, base_reward_rate=2.0)
    scores = calculate_total_score(
        card=card,
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        preferences=[],
        promotions=[],
    )
    # reward_score: 30000 * 2% = 600, max = 30000 * 5% = 1500, score = 40.0
    # feature_score: no prefs => 50.0
    # promotion_score: no promos => 0.0
    # roi_score: free card => 80.0
    # total = 40*0.40 + 50*0.25 + 0*0.15 + 80*0.20 = 16 + 12.5 + 0 + 16 = 44.5
    assert scores["total"] == 44.5


def test_total_score_custom_weights_backward_compat():
    """Custom weights with only old fields should still work."""
    card = CreditCard(name="Test", annual_fee=0, base_reward_rate=2.0)
    weights = ScoringWeights(
        reward=0.5, feature=0.3, promotion=0.2, annual_fee_roi=0.0
    )
    scores = calculate_total_score(
        card=card,
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        preferences=[],
        promotions=[],
        weights=weights,
    )
    # reward: 40*0.5=20, feature: 50*0.3=15, promo: 0*0.2=0, roi: 80*0=0
    # total = 35.0
    assert scores["total"] == 35.0


def test_recommendation_engine(db_session):
    engine = RecommendationEngine(db_session)

    request = RecommendRequest(
        spending_habits={"online_shopping": 0.5, "dining": 0.3, "others": 0.2},
        monthly_amount=30000,
        preferences=["no_annual_fee"],
        limit=5,
    )

    recommendations = engine.recommend(request)

    assert len(recommendations) == 1  # 年費卡被過濾掉
    assert recommendations[0].card.name == "高回饋卡"


def test_generate_reasons_expanded_categories():
    """Expanded category names like convenience_store should map to 超商."""
    engine = RecommendationEngine.__new__(RecommendationEngine)
    card = CreditCard(name="Test", annual_fee=0, base_reward_rate=2.0)
    request = RecommendRequest(
        spending_habits={"convenience_store": 0.6, "dining": 0.4},
        monthly_amount=30000,
        preferences=[],
    )
    scores = {
        "reward_score": 80,
        "feature_score": 50,
        "promotion_score": 0,
        "annual_fee_roi_score": 80,
    }
    reasons = engine._generate_reasons(card, request, scores, [])
    # Top category is convenience_store, should show "超商"
    assert any("超商" in r for r in reasons)


def test_generate_reasons_roi_reason():
    """When ROI score > 60, should mention annual fee ROI."""
    engine = RecommendationEngine.__new__(RecommendationEngine)
    card = CreditCard(name="Test", annual_fee=2000, base_reward_rate=3.0)
    request = RecommendRequest(
        spending_habits={"dining": 1.0},
        monthly_amount=50000,
        preferences=[],
    )
    scores = {
        "reward_score": 60,
        "feature_score": 50,
        "promotion_score": 0,
        "annual_fee_roi_score": 70,
    }
    reasons = engine._generate_reasons(card, request, scores, [])
    assert any("年費" in r and "回饋" in r for r in reasons)


def test_generate_reasons_reward_limit_warning():
    """When promotions have reward_limit, should warn about limits."""
    engine = RecommendationEngine.__new__(RecommendationEngine)
    card = CreditCard(name="Test", annual_fee=0, base_reward_rate=1.0)
    request = RecommendRequest(
        spending_habits={"dining": 1.0},
        monthly_amount=30000,
        preferences=[],
    )
    promo = Promotion(
        title="Dining", category="dining", reward_rate=5.0, reward_limit=200
    )
    scores = {
        "reward_score": 50,
        "feature_score": 50,
        "promotion_score": 25,
        "annual_fee_roi_score": 80,
    }
    reasons = engine._generate_reasons(card, request, scores, [promo])
    assert any("上限" in r for r in reasons)


def test_generate_reasons_high_rate_promo_callout():
    """High-rate promotions (>= 3%) should be called out specifically."""
    engine = RecommendationEngine.__new__(RecommendationEngine)
    card = CreditCard(name="Test", annual_fee=0, base_reward_rate=1.0)
    request = RecommendRequest(
        spending_habits={"dining": 0.5, "online_shopping": 0.5},
        monthly_amount=30000,
        preferences=[],
    )
    promo = Promotion(
        title="Dining Special", category="dining", reward_rate=8.0
    )
    scores = {
        "reward_score": 70,
        "feature_score": 50,
        "promotion_score": 40,
        "annual_fee_roi_score": 80,
    }
    reasons = engine._generate_reasons(card, request, scores, [promo])
    assert any("8" in r and "%" in r and "餐飲" in r for r in reasons)


def test_generate_reasons_max_five():
    """Reasons should be capped at 5."""
    engine = RecommendationEngine.__new__(RecommendationEngine)
    card = CreditCard(name="Test", annual_fee=0, base_reward_rate=3.0)
    request = RecommendRequest(
        spending_habits={"dining": 1.0},
        monthly_amount=50000,
        preferences=[],
    )
    promo = Promotion(
        title="Dining", category="dining", reward_rate=8.0, reward_limit=500
    )
    scores = {
        "reward_score": 90,
        "feature_score": 80,
        "promotion_score": 50,
        "annual_fee_roi_score": 80,
    }
    reasons = engine._generate_reasons(card, request, scores, [promo])
    assert len(reasons) <= 5
