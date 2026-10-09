"""Tests for encryption at rest, audit masking, bootstrap credentials, model IDs,
provider SDK calls, and web search."""

import sys
import types
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from cryptography.fernet import Fernet

import ai_providers
import auth
import data_protection
import database
import model_catalog
import privacy_scanner
import web_search
from database import session_scope
from models import Conversation, DetectionEvent, File, Message, Settings, User
from utils import add_message_to_conversation, create_new_conversation, get_conversation


def seed_user(username="user", password_hash="hash", **user_fields):
    with session_scope() as session:
        user = User(username=username, password=password_hash, role="user", **user_fields)
        session.add(user)
        session.flush()
        session.add(Settings(user_id=user.id))
        return user.id


def raw_value(table, column, row_id):
    with database.engine.connect() as conn:
        return conn.execute(sa.text(f"SELECT {column} FROM {table} WHERE id = :id"), {"id": row_id}).scalar()


# ---------------------------------------------------------------------------
# Encryption at rest
# ---------------------------------------------------------------------------

def test_message_title_and_filename_are_encrypted_at_rest(sqlite_db, monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    import tempfile as tempfile_module
    monkeypatch.setattr(tempfile_module, "tempdir", str(tmp_path))
    user_id = seed_user()
    conversation_id = create_new_conversation(user_id)

    message_id, error = add_message_to_conversation(
        conversation_id, "user", "my diagnosis is confidential",
        uploaded_files=[{"name": "john_smith_medical.pdf", "mime_type": "application/pdf", "content_bytes": b"%PDF"}],
    )
    assert error is None

    assert raw_value("messages", "content", message_id).startswith("enc:v1:")
    assert raw_value("conversations", "title", conversation_id).startswith("enc:v1:")
    with session_scope() as session:
        file_id = session.query(File.id).scalar()
    assert raw_value("files", "original_name", file_id).startswith("enc:v1:")

    conversation = get_conversation(conversation_id, requesting_user_id=user_id)
    assert conversation["title"] == "my diagnosis is confidential"
    assert conversation["messages"][0]["content"] == "my diagnosis is confidential"
    assert conversation["messages"][0]["files"][0]["original_name"] == "john_smith_medical.pdf"


def test_legacy_plaintext_is_readable_and_wrong_key_is_not_leaked(sqlite_db, monkeypatch):
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    user_id = seed_user()
    conversation_id = create_new_conversation(user_id)
    message_id, _ = add_message_to_conversation(conversation_id, "user", "legacy plaintext")
    assert raw_value("messages", "content", message_id) == "legacy plaintext"

    monkeypatch.setenv("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    assert get_conversation(conversation_id)["messages"][0]["content"] == "legacy plaintext"

    secret_id, _ = add_message_to_conversation(conversation_id, "assistant", "encrypted reply")
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", Fernet.generate_key().decode())  # wrong key
    contents = [m["content"] for m in get_conversation(conversation_id)["messages"]]
    assert data_protection.UNREADABLE_PLACEHOLDER in contents


def test_secure_existing_data_migration_encrypts_rotates_and_masks(sqlite_db, monkeypatch):
    import migration_secure_existing_data as migration

    monkeypatch.setattr(migration.database, "init_db", lambda: True)
    monkeypatch.delenv("DATA_ENCRYPTION_KEY", raising=False)
    user_id = seed_user()
    conversation_id = create_new_conversation(user_id)
    message_id, _ = add_message_to_conversation(conversation_id, "user", "old plaintext")
    with session_scope() as session:
        session.add(DetectionEvent(user_id=user_id, action="scan", severity="medium",
                                   detected_patterns={"ssn": ["123-45-6789"]}))
        session.add(DetectionEvent(user_id=user_id, action="block_sensitive_file", severity="high",
                                   detected_patterns={"sensitivity_label": ["Secret (secret)"]}))

    old_key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", old_key)
    assert migration.run_migration() is True
    first = raw_value("messages", "content", message_id)
    assert first.startswith("enc:v1:")

    new_key = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", f"{new_key},{old_key}")
    assert migration.run_migration() is True
    rotated = raw_value("messages", "content", message_id)
    assert rotated != first

    monkeypatch.setenv("DATA_ENCRYPTION_KEY", new_key)  # old key retired
    assert get_conversation(conversation_id)["messages"][0]["content"] == "old plaintext"

    with session_scope() as session:
        events = {e.action: e.get_detected_patterns() for e in session.query(DetectionEvent).all()}
    assert events["scan"] == {"ssn": ["***-**-6789"]}
    assert events["block_sensitive_file"] == {"sensitivity_label": ["Secret (secret)"]}  # labels untouched


# ---------------------------------------------------------------------------
# Audit log masking
# ---------------------------------------------------------------------------

def test_detection_events_store_masked_values_only(sqlite_db):
    user_id = seed_user()
    with session_scope() as session:
        session.query(Settings).filter(Settings.user_id == user_id).update({"scan_enabled": True, "scan_level": "standard"})

    privacy_scanner.scan_text(user_id, "ssn 123-45-6789 card 4111111111111111")

    with session_scope() as session:
        stored = session.query(DetectionEvent).one().get_detected_patterns()
    flattened = [value for values in stored.values() for value in values]
    assert "123-45-6789" not in flattened and "4111111111111111" not in flattened
    assert "***-**-6789" in flattened and "************1111" in flattened


# ---------------------------------------------------------------------------
# Bootstrap admin credentials
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("configured, expect_generated", [("", True), ("admin", True), ("short", True), ("a-Strong-Passphrase-42", False)])
def test_bootstrap_password_is_never_a_guessable_default(monkeypatch, configured, expect_generated):
    monkeypatch.setattr(auth, "CONFIGURED_BOOTSTRAP_ADMIN_PASSWORD", configured)
    password, generated = auth.resolve_bootstrap_password()
    assert generated is expect_generated
    assert password != "admin" and len(password) >= 8
    if not expect_generated:
        assert password == configured


def test_init_auth_creates_temporary_admin_and_logs_password_to_server_only(sqlite_db, monkeypatch, capsys):
    monkeypatch.setattr(auth, "CONFIGURED_BOOTSTRAP_ADMIN_PASSWORD", "")
    monkeypatch.setitem(sys.modules, "azure_auth", SimpleNamespace(init_azure_auth=lambda: None, check_azure_auth_params=lambda: None))

    auth.init_auth()

    output = capsys.readouterr().out
    password = output.split("Temporary password: ")[1].split()[0]
    success, user_id, role = auth.authenticate(auth.DEFAULT_BOOTSTRAP_ADMIN_USERNAME, password)
    assert success and role == "admin"
    import streamlit as st
    assert st.session_state.user_info["must_change_password"] is True
    assert auth.authenticate(auth.DEFAULT_BOOTSTRAP_ADMIN_USERNAME, "admin")[0] is False


def test_legacy_admin_admin_install_is_forced_to_change_password(sqlite_db):
    from utils_auth import hash_password
    user_id = seed_user(auth.DEFAULT_BOOTSTRAP_ADMIN_USERNAME, password_hash=hash_password("admin"))
    import streamlit as st

    assert auth.authenticate(auth.DEFAULT_BOOTSTRAP_ADMIN_USERNAME, "admin")[0] is True
    assert st.session_state.user_info["must_change_password"] is True


def test_admin_reset_marks_password_temporary_and_self_change_clears_it(sqlite_db):
    user_id = seed_user("employee")

    assert auth.update_user_password(user_id, "temporary-123", require_change=True)
    with session_scope() as session:
        assert session.get(User, user_id).must_change_password is True

    assert auth.update_user_password(user_id, "my-own-pass-456")
    with session_scope() as session:
        assert session.get(User, user_id).must_change_password is False

    assert auth.validate_password_strength("admin") is not None


# ---------------------------------------------------------------------------
# Model catalog
# ---------------------------------------------------------------------------

def test_retired_models_resolve_to_current_defaults(monkeypatch):
    for variable in ("OPENAI_MODELS", "CLAUDE_MODELS", "GEMINI_MODELS"):
        monkeypatch.delenv(variable, raising=False)
    assert model_catalog.resolve_model("openai", "gpt-4o") == model_catalog.default_model("openai")
    assert model_catalog.resolve_model("claude", "claude-3-5-sonnet-20241022") == "claude-sonnet-5-5"
    assert model_catalog.resolve_model("gemini", "gemini-1.5-pro") == "gemini-3.8-flash"
    assert model_catalog.resolve_model("claude", "claude-opus-5-5") == "claude-opus-5-5"
    assert model_catalog.resolve_model("local", "/models/x.gguf") == "/models/x.gguf"


def test_model_lists_can_be_overridden_from_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_MODELS", "gpt-7, gpt-7-mini")
    assert model_catalog.get_hosted_models()["openai"] == ["gpt-7", "gpt-7-mini"]
    assert model_catalog.resolve_model("openai", "gpt-5.5") == "gpt-7"


def test_new_settings_rows_use_current_models(sqlite_db):
    user_id = seed_user()
    with session_scope() as session:
        settings = session.query(Settings).filter(Settings.user_id == user_id).one()
        assert (settings.openai_model, settings.claude_model, settings.gemini_model) == (
            "gpt-5.6-terra", "claude-sonnet-5-5", "gemini-3.8-flash"
        )


# ---------------------------------------------------------------------------
# Provider SDK calls
# ---------------------------------------------------------------------------

def make_settings(**overrides):
    base = dict(user_id=1, openai_model="gpt-5.6-terra", claude_model="claude-sonnet-5-5", gemini_model="gemini-3.8-flash")
    base.update(overrides)
    return SimpleNamespace(**base)


def test_openai_uses_reasoning_compatible_parameters(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))])

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(ai_providers.openai, "OpenAI", lambda api_key: SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions())))

    assert ai_providers.get_openai_response(make_settings(), [{"role": "user", "content": "x"}], stream=False) == "hi"
    assert "max_tokens" not in captured and "temperature" not in captured
    assert captured["max_completion_tokens"] == ai_providers.MAX_OUTPUT_TOKENS
    assert captured["model"] == "gpt-5.6-terra"


def test_claude_omits_missing_system_prompt(monkeypatch):
    calls = []

    class FakeMessages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text="ok")])

    monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
    monkeypatch.setattr(ai_providers, "Anthropic", lambda api_key: SimpleNamespace(messages=FakeMessages()))

    ai_providers.get_claude_response(make_settings(), [{"role": "user", "content": "x"}], stream=False)
    ai_providers.get_claude_response(make_settings(), [{"role": "system", "content": "s"}, {"role": "user", "content": "x"}], stream=False)

    assert "system" not in calls[0] and calls[1]["system"] == "s"
    assert calls[0]["model"] == "claude-sonnet-5-5"


def test_gemini_uses_google_genai_with_system_instruction(monkeypatch):
    created = {}

    class FakeChat:
        def send_message_stream(self, message):
            created["message"] = message
            return iter([SimpleNamespace(text="Hel"), SimpleNamespace(text=None), SimpleNamespace(text="lo")])

    class FakeChats:
        def create(self, model, config, history):
            created.update(model=model, config=config, history=history)
            return FakeChat()

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    monkeypatch.setattr(ai_providers.genai, "Client", lambda api_key: SimpleNamespace(chats=FakeChats()))

    stream = ai_providers.get_gemini_response(
        make_settings(gemini_model="gemini-1.5-pro"),
        [
            {"role": "system", "content": "be brief"},
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
        ],
        stream=True,
    )

    assert "".join(stream) == "Hello"
    assert created["model"] == "gemini-3.8-flash"  # retired ID resolved
    assert created["config"].system_instruction == "be brief"
    assert [content.role for content in created["history"]] == ["user", "model"]
    assert created["message"] == "q2"


# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------

def test_search_web_uses_official_serpapi_client(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, api_key, timeout):
            captured.update(api_key=api_key, timeout=timeout)

        def search(self, params):
            captured["params"] = params
            return {"organic_results": [{"title": "T", "snippet": "S", "link": "https://x"}]}

    monkeypatch.setitem(sys.modules, "serpapi", types.SimpleNamespace(Client=FakeClient))
    monkeypatch.setenv("SERPAPI_KEY", "serp-key")

    results = web_search.search_web("privacy law")

    assert results == [{"title": "T", "snippet": "S", "link": "https://x"}]
    assert captured["params"] == {"engine": "google", "q": "privacy law", "num": 5}
    assert captured["api_key"] == "serp-key"
    assert "1. T\nS\nURL: https://x" in web_search.format_search_results("privacy law", results)


def test_search_web_reports_missing_key_and_legacy_package(monkeypatch):
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    with pytest.raises(web_search.WebSearchError, match="SERPAPI_KEY"):
        web_search.search_web("x")

    monkeypatch.setitem(sys.modules, "serpapi", types.SimpleNamespace(GoogleSearch=object))
    with pytest.raises(web_search.WebSearchError, match="google-search-results"):
        web_search.search_web("x", api_key="k")
