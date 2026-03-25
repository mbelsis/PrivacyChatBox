from datetime import datetime, timedelta, timezone

import auth
import privacy_scanner
from database import session_scope
from models import DetectionEvent, Settings, User
from utils import format_detection_events


def seed_user(username):
    with session_scope() as session:
        user = User(username=username, password="hash", role="user")
        session.add(user)
        session.flush()
        settings = Settings(user_id=user.id)
        session.add(settings)
        return user.id


def test_get_detection_events_filters_orders_and_includes_username(sqlite_db):
    user_a = seed_user("alice")
    user_b = seed_user("bob")
    now = datetime.now(timezone.utc)

    with session_scope() as session:
        session.add_all([
            DetectionEvent(
                user_id=user_a,
                timestamp=now - timedelta(minutes=5),
                action="scan",
                severity="medium",
                detected_patterns={"email": ["alice@example.com"]},
                file_names="a.txt",
            ),
            DetectionEvent(
                user_id=user_a,
                timestamp=now - timedelta(minutes=1),
                action="anonymize",
                severity="high",
                detected_patterns={"phone_number": ["5551234567"]},
                file_names="b.txt",
            ),
            DetectionEvent(
                user_id=user_b,
                timestamp=now - timedelta(minutes=2),
                action="scan",
                severity="low",
                detected_patterns={"url": ["https://example.com"]},
                file_names="c.txt",
            ),
        ])

    events = privacy_scanner.get_detection_events(user_id=user_a, limit=5, include_username=True)

    assert len(events) == 2
    assert events[0]["action"] == "anonymize"
    assert events[1]["action"] == "scan"
    assert all(event["user_id"] == user_a for event in events)
    assert all(event["username"] == "alice" for event in events)


def test_format_detection_events_formats_timestamp_and_counts_matches():
    event = DetectionEvent(
        id=9,
        user_id=4,
        timestamp=datetime(2026, 1, 2, 3, 4, 5),
        action="scan",
        severity="medium",
        detected_patterns={
            "email": ["a@example.com", "b@example.com"],
            "phone_number": ["5551234567"],
        },
        file_names="report.txt",
    )

    formatted = format_detection_events([event])

    assert formatted == [{
        "id": 9,
        "user_id": 4,
        "timestamp": "2026-01-02 03:04:05",
        "action": "scan",
        "severity": "medium",
        "file_names": "report.txt",
        "detected_patterns": {
            "email": ["a@example.com", "b@example.com"],
            "phone_number": ["5551234567"],
        },
        "detection_count": 3,
    }]
