from types import SimpleNamespace

import privacy_scanner


def test_anonymize_text_prefers_non_overlapping_matches(monkeypatch):
    monkeypatch.setattr(
        privacy_scanner,
        "scan_text",
        lambda user_id, text, **kwargs: (True, {"custom": ["abcd", "abc"]}),
    )
    monkeypatch.setattr(
        privacy_scanner,
        "get_user_settings",
        lambda user_id: SimpleNamespace(scan_enabled=True),
    )
    monkeypatch.setattr(privacy_scanner, "log_detection_event", lambda *args, **kwargs: None)

    anonymized, detected = privacy_scanner.anonymize_text(1, "xabcdz")

    assert anonymized == "x[REDACTED CUSTOM]z"
    assert detected == {"custom": ["abcd", "abc"]}
