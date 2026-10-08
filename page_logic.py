"""Shared pure helper logic extracted from Streamlit page modules."""

import re
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from utils import format_conversation_messages


def _value_or_default(value: Any, default: Any) -> Any:
    """Return ``default`` only when ``value`` is None.

    Using ``value or default`` silently turns legitimate zero values
    (``gpu_layers=0`` for CPU-only inference, ``temperature=0.0`` for
    deterministic output) into the defaults.
    """
    return default if value is None else value


def normalize_history_content(content: str) -> str:
    if not content:
        return ""
    normalized = re.sub(r"\[REDACTED [^\]]+\]", "[sensitive information]", content)
    normalized = normalized.replace("[CLASSIFIED DOCUMENT]", "[sensitive information]")
    return normalized


def build_chat_ai_messages(
    system_prompt: str,
    conversation_messages: List[Dict[str, Any]],
    current_message_id: Optional[int],
    current_user_content: str,
    character_changed: bool = False,
    role_name: Optional[str] = None,
    history_limit: int = 10,
) -> List[Dict[str, str]]:
    ai_messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

    # Sort before slicing so the history window really is the most recent turns.
    history_messages = format_conversation_messages([
        message for message in conversation_messages
        if message.get("id") != current_message_id
    ])[-history_limit:]

    if history_messages:
        for message_dict in history_messages:
            if message_dict["role"] != "system":
                ai_messages.append({
                    "role": message_dict["role"],
                    "content": normalize_history_content(message_dict["content"]),
                })

    if character_changed and role_name:
        ai_messages.append({
            "role": "user",
            "content": f"The user has changed your role. From now on, you will respond as a {role_name}.",
        })
        ai_messages.append({
            "role": "assistant",
            "content": f"I understand. I'll now be responding as a {role_name}.",
        })

    ai_messages.append({"role": "user", "content": current_user_content})
    return ai_messages


def get_local_model_settings_snapshot(settings: Any) -> Optional[Dict[str, Any]]:
    if not settings:
        return None
    return {
        "local_model_path": getattr(settings, "local_model_path", None),
        "local_model_context_size": _value_or_default(getattr(settings, "local_model_context_size", None), 2048),
        "local_model_gpu_layers": _value_or_default(getattr(settings, "local_model_gpu_layers", None), -1),
        "local_model_temperature": _value_or_default(getattr(settings, "local_model_temperature", None), 0.7),
        "disable_scan_for_local_model": _value_or_default(getattr(settings, "disable_scan_for_local_model", None), True),
    }


def merge_selected_model_snapshot(
    current_snapshot: Optional[Dict[str, Any]],
    selected_model: str,
    settings: Any,
) -> Dict[str, Any]:
    merged = dict(current_snapshot or {})
    merged.update({
        "local_model_path": selected_model,
        "local_model_context_size": _value_or_default(getattr(settings, "local_model_context_size", None), 2048),
        "local_model_gpu_layers": _value_or_default(getattr(settings, "local_model_gpu_layers", None), -1),
        "local_model_temperature": _value_or_default(getattr(settings, "local_model_temperature", None), 0.7),
        "disable_scan_for_local_model": _value_or_default(getattr(settings, "disable_scan_for_local_model", None), True),
    })
    return merged


def build_local_model_config_payload(
    context_size: int,
    gpu_layers: int,
    temperature: float,
    bypass_privacy: bool,
) -> Dict[str, Any]:
    return {
        "local_model_context_size": context_size,
        "local_model_gpu_layers": gpu_layers,
        "local_model_temperature": temperature,
        "disable_scan_for_local_model": bypass_privacy,
    }


def build_default_dlp_bulk_update(
    enabled: bool,
    threshold_value: str,
    apply_to_all: bool,
) -> Optional[Dict[str, Any]]:
    if not apply_to_all:
        return None
    return {
        "enable_ms_dlp": enabled,
        "ms_dlp_sensitivity_threshold": threshold_value,
    }


def event_timestamp_value(event_time: Any) -> Optional[float]:
    if hasattr(event_time, "timestamp"):
        return event_time.timestamp()
    if isinstance(event_time, str):
        try:
            return datetime.fromisoformat(event_time).timestamp()
        except ValueError:
            try:
                return datetime.strptime(event_time, "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                return None
    return None


def build_privacy_alert_index(detection_events: List[Dict[str, Any]]) -> Dict[Any, List[Any]]:
    privacy_alerts: Dict[Any, List[Any]] = {}
    for event in detection_events:
        event_user_id = event.get("user_id")
        event_timestamp = event.get("timestamp")
        if event_user_id not in privacy_alerts:
            privacy_alerts[event_user_id] = []
        privacy_alerts[event_user_id].append(event_timestamp)
    return privacy_alerts


def conversation_has_privacy_alert(
    conversation: Dict[str, Any],
    privacy_alerts: Dict[Any, List[Any]],
    time_window_seconds: int = 15 * 60,
) -> bool:
    user_id = conversation.get("user_id")
    updated_at = conversation.get("updated_at")
    if user_id not in privacy_alerts or not hasattr(updated_at, "timestamp"):
        return False

    conv_timestamp = updated_at.timestamp()
    for event_time in privacy_alerts[user_id]:
        parsed_timestamp = event_timestamp_value(event_time)
        if parsed_timestamp is None:
            continue
        if abs(parsed_timestamp - conv_timestamp) < time_window_seconds:
            return True
    return False


def build_history_conversation_rows(
    conversations: List[Dict[str, Any]],
    message_counts: Dict[int, Dict[str, int]],
    privacy_alerts: Dict[Any, List[Any]],
    is_admin: bool = False,
    users: Optional[Dict[Any, str]] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    users = users or {}

    for conv in conversations:
        count_info = message_counts.get(conv["id"], {"total": 0, "user": 0, "assistant": 0})
        row = {
            "ID": conv["id"],
            "Title": conv["title"],
            "Created": conv["created_at"].strftime("%Y-%m-%d %H:%M"),
            "Last Updated": conv["updated_at"].strftime("%Y-%m-%d %H:%M"),
            "Privacy Alert": "⚠️" if conversation_has_privacy_alert(conv, privacy_alerts) else "",
            "Messages": count_info["total"],
            "User Msgs": count_info["user"],
            "AI Msgs": count_info["assistant"],
        }
        if is_admin:
            row["Username"] = users.get(conv["user_id"], f"User {conv['user_id']}")
        rows.append(row)

    return rows


def format_time_bucket_key(date_obj: Any) -> str:
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d")
    if hasattr(date_obj, "strftime"):
        return date_obj.strftime("%Y-%m-%d")
    return str(date_obj)


def build_time_series_maps(rows: Dict[str, List[Any]]) -> Dict[str, Dict[str, int]]:
    formatted: Dict[str, Dict[str, int]] = {}
    for metric_name, metric_rows in rows.items():
        formatted[metric_name] = {
            format_time_bucket_key(date_obj): count
            for date_obj, count in metric_rows
        }
    return formatted


def build_time_series_rows(
    conversations_by_date: Dict[str, int],
    messages_by_date: Dict[str, int],
    detections_by_date: Dict[str, int],
) -> List[Dict[str, Any]]:
    all_dates = sorted(
        set(conversations_by_date.keys()) |
        set(messages_by_date.keys()) |
        set(detections_by_date.keys())
    )
    return [{
        "Date": date_str,
        "Conversations": conversations_by_date.get(date_str, 0),
        "Messages": messages_by_date.get(date_str, 0),
        "Privacy Events": detections_by_date.get(date_str, 0),
    } for date_str in all_dates]


def get_conversation_length_bucket(message_count: int) -> str:
    if message_count <= 2:
        return "1-2 messages"
    if message_count <= 5:
        return "3-5 messages"
    if message_count <= 10:
        return "6-10 messages"
    if message_count <= 20:
        return "11-20 messages"
    return "21+ messages"


def build_conversation_length_rows(conversation_counts: List[int]) -> List[Dict[str, Any]]:
    bucket_order = ["1-2 messages", "3-5 messages", "6-10 messages", "11-20 messages", "21+ messages"]
    buckets: Dict[str, int] = {}
    for count in conversation_counts:
        bucket = get_conversation_length_bucket(count)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    return [
        {"Length": bucket, "Conversations": buckets[bucket]}
        for bucket in bucket_order
        if bucket in buckets
    ]


def build_settings_snapshot(settings_row: Any) -> Optional[SimpleNamespace]:
    if not settings_row:
        return None
    return SimpleNamespace(
        id=getattr(settings_row, "id", None),
        user_id=getattr(settings_row, "user_id", None),
        llm_provider=getattr(settings_row, "llm_provider", "openai"),
        ai_character=getattr(settings_row, "ai_character", "assistant"),
        openai_api_key=getattr(settings_row, "openai_api_key", ""),
        openai_model=getattr(settings_row, "openai_model", "gpt-4o"),
        claude_api_key=getattr(settings_row, "claude_api_key", ""),
        claude_model=getattr(settings_row, "claude_model", "claude-3-5-sonnet-20241022"),
        gemini_api_key=getattr(settings_row, "gemini_api_key", ""),
        gemini_model=getattr(settings_row, "gemini_model", "gemini-1.5-pro"),
        serpapi_key=getattr(settings_row, "serpapi_key", ""),
        local_model_path=getattr(settings_row, "local_model_path", ""),
        local_model_context_size=getattr(settings_row, "local_model_context_size", None),
        local_model_gpu_layers=getattr(settings_row, "local_model_gpu_layers", None),
        local_model_temperature=getattr(settings_row, "local_model_temperature", None),
        scan_enabled=getattr(settings_row, "scan_enabled", True),
        scan_level=getattr(settings_row, "scan_level", "standard"),
        auto_anonymize=getattr(settings_row, "auto_anonymize", False),
        disable_scan_for_local_model=getattr(settings_row, "disable_scan_for_local_model", True),
        custom_patterns=list(getattr(settings_row, "custom_patterns", []) or []),
        enable_ms_dlp=getattr(settings_row, "enable_ms_dlp", True),
        ms_dlp_sensitivity_threshold=getattr(settings_row, "ms_dlp_sensitivity_threshold", "confidential"),
    )


def normalize_custom_patterns(patterns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    normalized = []
    for pattern in patterns or []:
        normalized.append({
            "name": (pattern.get("name") or "").strip(),
            "pattern": (pattern.get("pattern") or "").strip(),
            "level": pattern.get("level") if pattern.get("level") in {"standard", "strict"} else "standard",
        })
    return normalized


def validate_custom_patterns(patterns: List[Dict[str, Any]]) -> Tuple[List[Dict[str, str]], List[str]]:
    valid_patterns: List[Dict[str, str]] = []
    invalid_patterns: List[str] = []

    for pattern in normalize_custom_patterns(patterns):
        if not pattern["name"] and not pattern["pattern"]:
            continue
        if not pattern["name"] or not pattern["pattern"]:
            invalid_patterns.append("Each custom pattern requires both a name and a regex pattern.")
            continue
        try:
            re.compile(pattern["pattern"])
            valid_patterns.append(pattern)
        except re.error as exc:
            invalid_patterns.append(f"{pattern['name']}: {exc}")

    return valid_patterns, invalid_patterns


def build_privacy_settings_payload(
    scan_enabled: bool,
    scan_level: str,
    auto_anonymize: bool,
    disable_scan_for_local_model: bool,
) -> Dict[str, Any]:
    return {
        "scan_enabled": scan_enabled,
        "scan_level": scan_level,
        "auto_anonymize": auto_anonymize,
        "disable_scan_for_local_model": disable_scan_for_local_model,
    }


def build_admin_privacy_log_rows(
    formatted_events: List[Dict[str, Any]],
    users_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    username_by_id = {user["id"]: user["username"] for user in users_data}
    return [{
        "Timestamp": event["timestamp"],
        "Username": username_by_id.get(event["user_id"], "Unknown"),
        "Action": event["action"].capitalize(),
        "Severity": event["severity"].capitalize(),
        "Detections": event["detection_count"],
        "File": event["file_names"] if event["file_names"] else "N/A",
    } for event in formatted_events]


def get_admin_count(users: List[Dict[str, Any]]) -> int:
    return sum(1 for user in users if user.get("role") == "admin")


def can_change_user_role(
    acting_user_id: int,
    target_user: Optional[Dict[str, Any]],
    new_role: str,
    admin_count: int,
    is_bootstrap_account_fn,
) -> Tuple[bool, Optional[str]]:
    if not target_user:
        return False, "User not found."
    if acting_user_id == target_user["id"] and new_role != "admin":
        return False, "You cannot remove your own admin privileges"
    if is_bootstrap_account_fn(target_user["username"]) and new_role != "admin":
        return False, "You cannot remove admin privileges from the bootstrap admin account."
    if target_user.get("role") == "admin" and new_role != "admin" and admin_count <= 1:
        return False, "You cannot demote the last remaining admin account."
    return True, None


def can_delete_user_account(
    acting_user_id: int,
    target_user: Optional[Dict[str, Any]],
    admin_count: int,
    is_bootstrap_account_fn,
) -> Tuple[bool, Optional[str]]:
    if not target_user:
        return False, "User not found."
    if target_user["id"] == acting_user_id:
        return False, "You cannot delete your own account"
    if is_bootstrap_account_fn(target_user["username"]):
        return False, "You cannot delete the bootstrap admin account."
    if target_user.get("role") == "admin" and admin_count <= 1:
        return False, "You cannot delete the last remaining admin account."
    return True, None


def build_file_payloads(files: List[Any]) -> List[Dict[str, Any]]:
    """Build scan/AI payloads for uploaded files.

    Binary document formats (PDF, DOCX, XLSX, PPTX) are converted to text with the
    extractors in ``file_processor``; decoding their raw bytes would produce garbage
    that is neither scannable nor useful to the AI model.
    """
    from file_processor import extract_text_from_bytes

    payloads: List[Dict[str, Any]] = []
    for file in files or []:
        original_bytes = file.getvalue()
        mime_type = file.type or "application/octet-stream"
        payloads.append({
            "name": file.name,
            "mime_type": mime_type,
            "content": extract_text_from_bytes(file.name, mime_type, original_bytes),
            "content_bytes": original_bytes,
        })
    return payloads


def build_uploaded_file_records(file_payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{
        "name": file_payload["name"],
        "mime_type": file_payload["mime_type"],
        "content_bytes": file_payload["content_bytes"],
    } for file_payload in file_payloads]


def build_admin_stats_summary(
    total_users: int,
    total_conversations: int,
    total_detection_events: int,
    most_conversations_row: Optional[Tuple[Any, Any, Any]],
    latest_event_data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    summary = {
        "total_users": total_users,
        "total_conversations": total_conversations,
        "total_detection_events": total_detection_events,
        "most_active_user": None,
        "latest_event": None,
    }

    if most_conversations_row:
        username, user_id, count = most_conversations_row
        summary["most_active_user"] = {
            "username": username,
            "user_id": user_id,
            "conversation_count": count,
        }

    if latest_event_data:
        timestamp = latest_event_data.get("timestamp")
        summary["latest_event"] = {
            "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(timestamp, "strftime") else str(timestamp),
            "action": latest_event_data.get("action"),
            "severity": latest_event_data.get("severity"),
        }

    return summary


def build_current_user_content(
    final_message: str,
    search_results: str = "",
    file_context: str = "",
) -> str:
    return f"{final_message}{search_results or ''}{file_context or ''}"


def get_chat_provider_precheck_error(
    selected_provider: str,
    settings: Any,
    openai_key: str = "",
    claude_key: str = "",
    gemini_key: str = "",
) -> Optional[str]:
    if selected_provider == "openai" and not openai_key:
        return "⚠️ OpenAI API key not found in environment variables. Please add your API key to your .env file or environment variables with the key OPENAI_API_KEY."
    if selected_provider == "claude" and not claude_key:
        return "⚠️ Claude API key not found in environment variables. Please add your API key to your .env file or environment variables with the key ANTHROPIC_API_KEY."
    if selected_provider == "gemini" and not gemini_key:
        return "⚠️ Gemini API key not found in environment variables. Please add your API key to your .env file or environment variables with the key GOOGLE_API_KEY."
    if selected_provider == "local" and not getattr(settings, "local_model_path", ""):
        return "⚠️ Local model path not configured. Please add a model path in the settings."
    return None


def build_admin_user_filter_options(users_data: List[Dict[str, Any]]) -> Dict[str, Optional[int]]:
    options = {"All Users": None}
    for user in users_data:
        options[f"{user['username']} (ID: {user['id']})"] = user["id"]
    return options


def build_event_pattern_detail_lines(detected_patterns: Dict[str, List[str]]) -> List[str]:
    lines: List[str] = []
    for pattern_type, matches in detected_patterns.items():
        preview = ", ".join(matches[:3])
        suffix = f" and {len(matches) - 3} more" if len(matches) > 3 else ""
        lines.append(f"- **{pattern_type}**: {preview}{suffix}")
    return lines
