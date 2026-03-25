from types import SimpleNamespace

from page_logic import (
    build_default_dlp_bulk_update,
    build_local_model_config_payload,
    build_privacy_settings_payload,
    build_settings_snapshot,
    get_local_model_settings_snapshot,
    merge_selected_model_snapshot,
    normalize_custom_patterns,
    validate_custom_patterns,
)


def test_get_local_model_settings_snapshot_applies_defaults():
    settings = SimpleNamespace(
        local_model_path="models/demo.gguf",
        local_model_context_size=None,
        local_model_gpu_layers=None,
        local_model_temperature=None,
        disable_scan_for_local_model=None,
    )

    snapshot = get_local_model_settings_snapshot(settings)

    assert snapshot == {
        "local_model_path": "models/demo.gguf",
        "local_model_context_size": 2048,
        "local_model_gpu_layers": -1,
        "local_model_temperature": 0.7,
        "disable_scan_for_local_model": True,
    }


def test_merge_selected_model_snapshot_preserves_existing_fields_and_refreshes_defaults():
    current = {"local_model_path": "old.gguf", "extra": "keep"}
    settings = SimpleNamespace(
        local_model_context_size=4096,
        local_model_gpu_layers=12,
        local_model_temperature=0.2,
        disable_scan_for_local_model=False,
    )

    merged = merge_selected_model_snapshot(current, "new.gguf", settings)

    assert merged == {
        "local_model_path": "new.gguf",
        "local_model_context_size": 4096,
        "local_model_gpu_layers": 12,
        "local_model_temperature": 0.2,
        "disable_scan_for_local_model": False,
        "extra": "keep",
    }


def test_build_local_model_config_payload_returns_expected_mapping():
    assert build_local_model_config_payload(8192, 8, 0.55, True) == {
        "local_model_context_size": 8192,
        "local_model_gpu_layers": 8,
        "local_model_temperature": 0.55,
        "disable_scan_for_local_model": True,
    }


def test_build_default_dlp_bulk_update_requires_apply_to_all():
    assert build_default_dlp_bulk_update(True, "confidential", False) is None
    assert build_default_dlp_bulk_update(False, "internal", True) == {
        "enable_ms_dlp": False,
        "ms_dlp_sensitivity_threshold": "internal",
    }


def test_build_settings_snapshot_copies_scalar_values_without_orm_dependency():
    settings_row = SimpleNamespace(
        id=1,
        user_id=9,
        llm_provider="claude",
        ai_character="programmer",
        claude_model="claude-model",
        scan_enabled=False,
        scan_level="strict",
        auto_anonymize=True,
        disable_scan_for_local_model=False,
        custom_patterns=[{"name": "x", "pattern": "y", "level": "strict"}],
    )

    snapshot = build_settings_snapshot(settings_row)

    assert snapshot.user_id == 9
    assert snapshot.llm_provider == "claude"
    assert snapshot.ai_character == "programmer"
    assert snapshot.scan_level == "strict"
    assert snapshot.custom_patterns == [{"name": "x", "pattern": "y", "level": "strict"}]


def test_normalize_and_validate_custom_patterns():
    valid_patterns, invalid_patterns = validate_custom_patterns([
        {"name": " token ", "pattern": " tok_[a-z]+ ", "level": "strict"},
        {"name": "", "pattern": "", "level": "standard"},
        {"name": "missing-pattern", "pattern": "", "level": "standard"},
        {"name": "broken", "pattern": "(", "level": "weird"},
    ])

    assert normalize_custom_patterns([{"name": " a ", "pattern": " b ", "level": "weird"}]) == [{
        "name": "a",
        "pattern": "b",
        "level": "standard",
    }]
    assert valid_patterns == [{
        "name": "token",
        "pattern": "tok_[a-z]+",
        "level": "strict",
    }]
    assert len(invalid_patterns) == 2
    assert invalid_patterns[0] == "Each custom pattern requires both a name and a regex pattern."
    assert invalid_patterns[1].startswith("broken:")


def test_build_privacy_settings_payload_returns_expected_mapping():
    assert build_privacy_settings_payload(True, "strict", False, True) == {
        "scan_enabled": True,
        "scan_level": "strict",
        "auto_anonymize": False,
        "disable_scan_for_local_model": True,
    }
