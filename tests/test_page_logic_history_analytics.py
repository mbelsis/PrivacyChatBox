from datetime import datetime

from page_logic import (
    build_conversation_length_rows,
    build_history_conversation_rows,
    build_privacy_alert_index,
    build_time_series_maps,
    build_time_series_rows,
    conversation_has_privacy_alert,
    event_timestamp_value,
    format_time_bucket_key,
)


def test_event_timestamp_value_accepts_datetime_and_string_formats():
    dt_value = datetime(2026, 1, 2, 3, 4, 5)
    iso_value = "2026-01-02T03:04:05"
    legacy_value = "2026-01-02 03:04:05"

    assert event_timestamp_value(dt_value) == dt_value.timestamp()
    assert event_timestamp_value(iso_value) == dt_value.timestamp()
    assert event_timestamp_value(legacy_value) == dt_value.timestamp()
    assert event_timestamp_value("not-a-date") is None


def test_privacy_alert_helpers_index_and_match_conversation_window():
    updated_at = datetime(2026, 1, 1, 12, 0, 0)
    conversation = {"user_id": 3, "updated_at": updated_at}
    events = [
        {"user_id": 3, "timestamp": "2026-01-01 11:50:30"},
        {"user_id": 4, "timestamp": "2026-01-01 12:00:00"},
    ]

    privacy_alerts = build_privacy_alert_index(events)

    assert privacy_alerts == {3: ["2026-01-01 11:50:30"], 4: ["2026-01-01 12:00:00"]}
    assert conversation_has_privacy_alert(conversation, privacy_alerts) is True
    assert conversation_has_privacy_alert({"user_id": 99, "updated_at": updated_at}, privacy_alerts) is False


def test_build_history_conversation_rows_adds_counts_privacy_and_username():
    conversations = [{
        "id": 10,
        "user_id": 7,
        "title": "Conversation",
        "created_at": datetime(2026, 1, 1, 10, 0, 0),
        "updated_at": datetime(2026, 1, 1, 10, 10, 0),
    }]
    message_counts = {10: {"total": 4, "user": 2, "assistant": 2}}
    privacy_alerts = {7: ["2026-01-01 10:08:00"]}

    rows = build_history_conversation_rows(
        conversations=conversations,
        message_counts=message_counts,
        privacy_alerts=privacy_alerts,
        is_admin=True,
        users={7: "alice"},
    )

    assert rows == [{
        "ID": 10,
        "Title": "Conversation",
        "Created": "2026-01-01 10:00",
        "Last Updated": "2026-01-01 10:10",
        "Privacy Alert": "⚠️",
        "Messages": 4,
        "User Msgs": 2,
        "AI Msgs": 2,
        "Username": "alice",
    }]


def test_analytics_time_series_helpers_format_and_merge_buckets():
    dt = datetime(2026, 1, 1, 0, 0, 0)
    maps = build_time_series_maps({
        "conversations": [(dt, 2)],
        "messages": [("2026-01-02", 5)],
        "detections": [],
    })

    assert format_time_bucket_key(dt) == "2026-01-01"
    assert maps == {
        "conversations": {"2026-01-01": 2},
        "messages": {"2026-01-02": 5},
        "detections": {},
    }

    rows = build_time_series_rows(
        conversations_by_date=maps["conversations"],
        messages_by_date=maps["messages"],
        detections_by_date={"2026-01-01": 1},
    )

    assert rows == [
        {"Date": "2026-01-01", "Conversations": 2, "Messages": 0, "Privacy Events": 1},
        {"Date": "2026-01-02", "Conversations": 0, "Messages": 5, "Privacy Events": 0},
    ]


def test_conversation_length_rows_bucket_and_order_counts():
    rows = build_conversation_length_rows([1, 2, 3, 7, 18, 25, 25])

    assert rows == [
        {"Length": "1-2 messages", "Conversations": 2},
        {"Length": "3-5 messages", "Conversations": 1},
        {"Length": "6-10 messages", "Conversations": 1},
        {"Length": "11-20 messages", "Conversations": 1},
        {"Length": "21+ messages", "Conversations": 2},
    ]
