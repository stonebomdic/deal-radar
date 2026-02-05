from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models import Bank, CreditCard, Promotion


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_data(db_session):
    """Create sample bank, card, and promotion data."""
    bank = Bank(name="Test Bank", code="test", website="https://test.com")
    db_session.add(bank)
    db_session.commit()

    card = CreditCard(
        bank_id=bank.id,
        name="Test Card",
        card_type="Visa",
        annual_fee=0,
        base_reward_rate=1.0,
    )
    db_session.add(card)
    db_session.commit()

    # A promotion created today (explicitly set created_at to local now,
    # since server_default uses UTC CURRENT_TIMESTAMP in SQLite)
    promo_new = Promotion(
        card_id=card.id,
        title="New Promo Today",
        category="online_shopping",
        reward_type="cashback",
        reward_rate=3.0,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
    )
    promo_new.created_at = datetime.now()

    # A promotion expiring in 2 days
    promo_expiring = Promotion(
        card_id=card.id,
        title="Expiring Soon",
        category="dining",
        reward_type="points",
        reward_rate=5.0,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=2),
    )

    db_session.add_all([promo_new, promo_expiring])
    db_session.commit()

    return {
        "bank": bank,
        "card": card,
        "promo_new": promo_new,
        "promo_expiring": promo_expiring,
    }


class TestCheckNewPromotions:
    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_notifies_new_promotions(
        self, mock_get_session, mock_dispatcher_cls, db_session, sample_data
    ):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"telegram": 1}
        mock_dispatcher_cls.return_value = mock_dispatcher

        from src.scheduler.jobs import check_new_promotions

        check_new_promotions()

        # Dispatcher should have been called (promotions were created today)
        mock_dispatcher.dispatch.assert_called_once()
        call_args = mock_dispatcher.dispatch.call_args
        from src.models.notification_log import NotificationType

        assert call_args.args[0] == NotificationType.new_promotion

    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_no_notification_when_no_new_promos(
        self, mock_get_session, mock_dispatcher_cls, db_session
    ):
        """No promotions created today -> no dispatch."""
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        from src.scheduler.jobs import check_new_promotions

        check_new_promotions()

        mock_dispatcher_cls.assert_not_called()


class TestCheckExpiringPromotions:
    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_notifies_expiring_promotions(
        self, mock_get_session, mock_dispatcher_cls, db_session, sample_data
    ):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_dispatcher = MagicMock()
        mock_dispatcher.dispatch.return_value = {"telegram": 1}
        mock_dispatcher_cls.return_value = mock_dispatcher

        from src.scheduler.jobs import check_expiring_promotions

        check_expiring_promotions()

        mock_dispatcher.dispatch.assert_called_once()
        call_args = mock_dispatcher.dispatch.call_args
        from src.models.notification_log import NotificationType

        assert call_args.args[0] == NotificationType.expiring_promotion

    @patch("src.scheduler.jobs.NotificationDispatcher")
    @patch("src.scheduler.jobs.get_sync_session")
    def test_no_notification_when_nothing_expiring(
        self, mock_get_session, mock_dispatcher_cls, db_session
    ):
        """No promotions expiring in 3 days -> no dispatch."""
        # Add a promotion expiring in 10 days (outside 3-day window)
        bank = Bank(name="Test", code="test")
        db_session.add(bank)
        db_session.commit()

        card = CreditCard(bank_id=bank.id, name="Card")
        db_session.add(card)
        db_session.commit()

        promo = Promotion(
            card_id=card.id,
            title="Far Future Promo",
            end_date=date.today() + timedelta(days=10),
        )
        db_session.add(promo)
        db_session.commit()

        mock_get_session.return_value.__enter__ = MagicMock(return_value=db_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        from src.scheduler.jobs import check_expiring_promotions

        check_expiring_promotions()

        mock_dispatcher_cls.assert_not_called()
