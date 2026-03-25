import sys
import types
from types import SimpleNamespace

import ai_providers


def make_settings(**overrides):
    base = {
        "id": 1,
        "user_id": 7,
        "llm_provider": "openai",
        "ai_character": "assistant",
        "openai_api_key": "",
        "openai_model": "gpt-4o",
        "claude_api_key": "",
        "claude_model": "claude-3-5-sonnet-20241022",
        "gemini_api_key": "",
        "gemini_model": "gemini-1.5-pro",
        "serpapi_key": "",
        "local_model_path": "",
        "local_model_context_size": 2048,
        "local_model_gpu_layers": -1,
        "local_model_temperature": 0.7,
        "scan_enabled": True,
        "scan_level": "strict",
        "auto_anonymize": False,
        "disable_scan_for_local_model": False,
        "custom_patterns": [{"name": "token", "pattern": r"tok_[a-z]+"}],
        "enable_ms_dlp": True,
        "ms_dlp_sensitivity_threshold": "confidential",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_get_ai_response_uses_overrides_without_mutating_settings(monkeypatch):
    settings = make_settings()
    captured = {}

    monkeypatch.setattr(ai_providers, "get_user_settings", lambda user_id: settings)

    def fake_openai_response(settings_copy, messages, stream):
        captured["provider"] = settings_copy.llm_provider
        captured["model"] = settings_copy.openai_model
        settings_copy.custom_patterns.append({"name": "extra", "pattern": "x"})
        return "ok"

    monkeypatch.setattr(ai_providers, "get_openai_response", fake_openai_response)

    result = ai_providers.get_ai_response(
        user_id=7,
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
        override_provider="openai",
        override_model="gpt-4-turbo",
        input_already_processed=True,
    )

    assert result == "ok"
    assert captured == {"provider": "openai", "model": "gpt-4-turbo"}
    assert settings.openai_model == "gpt-4o"
    assert settings.custom_patterns == [{"name": "token", "pattern": r"tok_[a-z]+"}]


def test_get_ai_response_skips_scan_when_input_already_processed(monkeypatch):
    settings = make_settings(auto_anonymize=False)
    fake_privacy = types.ModuleType("privacy_scanner")
    calls = {"scan": 0, "anonymize": 0}

    fake_privacy.scan_text = lambda user_id, text: calls.__setitem__("scan", calls["scan"] + 1)
    fake_privacy.anonymize_text = lambda user_id, text: (
        calls.__setitem__("anonymize", calls["anonymize"] + 1),
        ["unexpected"],
    )

    monkeypatch.setattr(ai_providers, "get_user_settings", lambda user_id: settings)
    monkeypatch.setattr(ai_providers, "get_openai_response", lambda settings_copy, messages, stream: "ok")
    monkeypatch.setitem(sys.modules, "privacy_scanner", fake_privacy)

    result = ai_providers.get_ai_response(
        user_id=7,
        messages=[{"role": "user", "content": "already sanitized"}],
        stream=False,
        input_already_processed=True,
    )

    assert result == "ok"
    assert calls == {"scan": 0, "anonymize": 0}


def test_get_ai_response_bypasses_scan_for_local_models(monkeypatch):
    settings = make_settings(
        llm_provider="local",
        disable_scan_for_local_model=True,
        auto_anonymize=True,
        local_model_path="models/demo.gguf",
    )
    fake_privacy = types.ModuleType("privacy_scanner")
    calls = {"scan": 0, "anonymize": 0}

    def fake_scan_text(user_id, text):
        calls["scan"] += 1
        return {}

    def fake_anonymize_text(user_id, text):
        calls["anonymize"] += 1
        return "[REDACTED]", ["email"]

    fake_privacy.scan_text = fake_scan_text
    fake_privacy.anonymize_text = fake_anonymize_text

    monkeypatch.setattr(ai_providers, "get_user_settings", lambda user_id: settings)
    monkeypatch.setattr(ai_providers, "get_local_response", lambda settings_copy, messages, stream: "local-ok")
    monkeypatch.setitem(sys.modules, "privacy_scanner", fake_privacy)

    result = ai_providers.get_ai_response(
        user_id=7,
        messages=[{"role": "user", "content": "secret@example.com"}],
        stream=False,
    )

    assert result == "local-ok"
    assert calls == {"scan": 0, "anonymize": 0}
