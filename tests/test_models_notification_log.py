import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.database import Base
from src.models.notification_log import (
    NotificationChannel,
    NotificationLog,
    NotificationType,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_create_notification_log(db_session):
    log = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=1,
        channel=NotificationChannel.telegram,
    )
    db_session.add(log)
    db_session.commit()

    assert log.id is not None
    assert log.notification_type == NotificationType.new_promotion
    assert log.reference_id == 1
    assert log.channel == NotificationChannel.telegram
    assert log.sent_at is not None


def test_notification_log_repr(db_session):
    log = NotificationLog(
        notification_type=NotificationType.expiring_promotion,
        reference_id=42,
        channel=NotificationChannel.discord,
    )
    db_session.add(log)
    db_session.commit()

    assert "expiring_promotion" in repr(log)
    assert "42" in repr(log)
    assert "discord" in repr(log)


def test_notification_log_dedup_constraint(db_session):
    """Same (notification_type, reference_id, channel) should raise IntegrityError."""
    log1 = NotificationLog(
        notification_type=NotificationType.new_card,
        reference_id=10,
        channel=NotificationChannel.telegram,
    )
    db_session.add(log1)
    db_session.commit()

    log2 = NotificationLog(
        notification_type=NotificationType.new_card,
        reference_id=10,
        channel=NotificationChannel.telegram,
    )
    db_session.add(log2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_notification_log_different_channel_allowed(db_session):
    """Same type+reference but different channel should be allowed."""
    log1 = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=5,
        channel=NotificationChannel.telegram,
    )
    log2 = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=5,
        channel=NotificationChannel.discord,
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    assert log1.id is not None
    assert log2.id is not None
    assert log1.id != log2.id


def test_notification_log_different_type_allowed(db_session):
    """Same reference+channel but different type should be allowed."""
    log1 = NotificationLog(
        notification_type=NotificationType.new_promotion,
        reference_id=5,
        channel=NotificationChannel.telegram,
    )
    log2 = NotificationLog(
        notification_type=NotificationType.expiring_promotion,
        reference_id=5,
        channel=NotificationChannel.telegram,
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    assert log1.id is not None
    assert log2.id is not None
