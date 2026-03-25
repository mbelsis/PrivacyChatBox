from datetime import datetime, timedelta
from types import SimpleNamespace

from page_logic import (
    build_chat_ai_messages,
    build_current_user_content,
    build_file_payloads,
    build_uploaded_file_records,
    get_chat_provider_precheck_error,
)


def test_build_chat_ai_messages_normalizes_history_and_keeps_current_turn_last():
    base = datetime(2026, 1, 1, 12, 0, 0)
    conversation_messages = [
        {"id": 1, "role": "user", "content": "Earlier [REDACTED EMAIL]", "timestamp": base},
        {"id": 2, "role": "assistant", "content": "Reply [CLASSIFIED DOCUMENT]", "timestamp": base + timedelta(minutes=1)},
        {"id": 99, "role": "user", "content": "Current saved message", "timestamp": base + timedelta(minutes=2)},
    ]

    messages = build_chat_ai_messages(
        system_prompt="system",
        conversation_messages=conversation_messages,
        current_message_id=99,
        current_user_content="Current final content with file context",
        character_changed=True,
        role_name="Privacy Expert",
    )

    assert messages[0] == {"role": "system", "content": "system"}
    assert messages[1]["content"] == "Earlier [sensitive information]"
    assert messages[2]["content"] == "Reply [sensitive information]"
    assert messages[3]["role"] == "user"
    assert "Privacy Expert" in messages[3]["content"]
    assert messages[4]["role"] == "assistant"
    assert "Privacy Expert" in messages[4]["content"]
    assert messages[-1] == {"role": "user", "content": "Current final content with file context"}
    assert all(message.get("content") != "Current saved message" for message in messages)


def test_build_file_payloads_and_uploaded_records_preserve_bytes_and_metadata():
    class FakeUpload:
        def __init__(self, name, content_type, content):
            self.name = name
            self.type = content_type
            self._content = content

        def getvalue(self):
            return self._content

    uploads = [
        FakeUpload("a.txt", "text/plain", b"hello"),
        FakeUpload("b.bin", None, b"\xff\xfe"),
    ]

    payloads = build_file_payloads(uploads)
    records = build_uploaded_file_records(payloads)

    assert payloads[0]["content"] == "hello"
    assert payloads[1]["mime_type"] == "application/octet-stream"
    assert payloads[1]["content_bytes"] == b"\xff\xfe"
    assert records == [
        {"name": "a.txt", "mime_type": "text/plain", "content_bytes": b"hello"},
        {"name": "b.bin", "mime_type": "application/octet-stream", "content_bytes": b"\xff\xfe"},
    ]


def test_build_current_user_content_appends_search_and_file_context():
    assert build_current_user_content("hello", "\nsearch", "\nfile") == "hello\nsearch\nfile"
    assert build_current_user_content("hello") == "hello"


def test_get_chat_provider_precheck_error_covers_missing_keys_and_local_model():
    settings = SimpleNamespace(local_model_path="")

    assert "OPENAI_API_KEY" in get_chat_provider_precheck_error("openai", settings, openai_key="")
    assert "ANTHROPIC_API_KEY" in get_chat_provider_precheck_error("claude", settings, claude_key="")
    assert "GOOGLE_API_KEY" in get_chat_provider_precheck_error("gemini", settings, gemini_key="")
    assert "Local model path not configured" in get_chat_provider_precheck_error("local", settings)
    assert get_chat_provider_precheck_error("openai", settings, openai_key="set") is None
