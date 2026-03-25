from datetime import datetime

from page_logic import (
    build_admin_privacy_log_rows,
    build_admin_stats_summary,
    build_admin_user_filter_options,
    build_event_pattern_detail_lines,
    can_change_user_role,
    can_delete_user_account,
    get_admin_count,
)


def test_build_admin_privacy_log_rows_maps_usernames_and_formats_defaults():
    rows = build_admin_privacy_log_rows(
        formatted_events=[{
            "timestamp": "2026-01-01 10:00:00",
            "user_id": 3,
            "action": "scan",
            "severity": "high",
            "detection_count": 4,
            "file_names": "",
        }],
        users_data=[{"id": 3, "username": "alice"}],
    )

    assert rows == [{
        "Timestamp": "2026-01-01 10:00:00",
        "Username": "alice",
        "Action": "Scan",
        "Severity": "High",
        "Detections": 4,
        "File": "N/A",
    }]


def test_admin_role_and_delete_guards_protect_bootstrap_and_last_admin():
    users = [
        {"id": 1, "username": "admin", "role": "admin"},
        {"id": 2, "username": "bob", "role": "user"},
    ]
    is_bootstrap = lambda username: username == "admin"

    assert get_admin_count(users) == 1

    allowed, message = can_change_user_role(acting_user_id=1, target_user=users[0], new_role="user", admin_count=1, is_bootstrap_account_fn=is_bootstrap)
    assert allowed is False
    assert message == "You cannot remove your own admin privileges"

    allowed, message = can_delete_user_account(acting_user_id=2, target_user=users[0], admin_count=1, is_bootstrap_account_fn=is_bootstrap)
    assert allowed is False
    assert message == "You cannot delete the bootstrap admin account."

    allowed, message = can_delete_user_account(acting_user_id=1, target_user=users[1], admin_count=1, is_bootstrap_account_fn=is_bootstrap)
    assert allowed is True
    assert message is None


def test_build_admin_stats_summary_formats_optional_rows():
    summary = build_admin_stats_summary(
        total_users=4,
        total_conversations=12,
        total_detection_events=3,
        most_conversations_row=("alice", 7, 5),
        latest_event_data={
            "timestamp": datetime(2026, 1, 1, 12, 30, 0),
            "action": "scan",
            "severity": "high",
        },
    )

    assert summary == {
        "total_users": 4,
        "total_conversations": 12,
        "total_detection_events": 3,
        "most_active_user": {
            "username": "alice",
            "user_id": 7,
            "conversation_count": 5,
        },
        "latest_event": {
            "timestamp": "2026-01-01 12:30:00",
            "action": "scan",
            "severity": "high",
        },
    }


def test_build_admin_user_filter_options_and_event_detail_lines():
    assert build_admin_user_filter_options([
        {"id": 2, "username": "alice"},
        {"id": 5, "username": "bob"},
    ]) == {
        "All Users": None,
        "alice (ID: 2)": 2,
        "bob (ID: 5)": 5,
    }

    assert build_event_pattern_detail_lines({
        "email": ["a@example.com", "b@example.com", "c@example.com", "d@example.com"],
        "phone": ["123"],
    }) == [
        "- **email**: a@example.com, b@example.com, c@example.com and 1 more",
        "- **phone**: 123",
    ]
