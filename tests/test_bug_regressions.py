"""Regression tests for logic bugs fixed during the code audit."""

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import azure_auth
import file_processor
import privacy_scanner
import utils
from database import session_scope
from models import Conversation, DetectionEvent, File, Message, Settings, User
from page_logic import build_chat_ai_messages, build_file_payloads, get_local_model_settings_snapshot
from utils import add_message_to_conversation, create_new_conversation, get_conversation


def seed_user(username, **settings_overrides):
    with session_scope() as session:
        user = User(username=username, password="hash", role="user")
        session.add(user)
        session.flush()
        session.add(Settings(user_id=user.id, **settings_overrides))
        return user.id


# ---------------------------------------------------------------------------
# utils.add_message_to_conversation: a DLP block must not persist anything
# ---------------------------------------------------------------------------

def test_dlp_block_leaves_no_message_and_removes_temp_file(sqlite_db, monkeypatch, tmp_path):
    user_id = seed_user("dlp-user")
    conversation_id = create_new_conversation(user_id)

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(utils, "MS_DLP_AVAILABLE", True)
    monkeypatch.setattr(utils, "is_dlp_integration_enabled", lambda uid: True, raising=False)
    monkeypatch.setattr(
        utils,
        "scan_file_for_sensitivity",
        lambda **kwargs: (False, "File blocked due to Microsoft sensitivity label: Secret."),
        raising=False,
    )

    message_id, error = add_message_to_conversation(
        conversation_id,
        "user",
        "please review the attached file",
        uploaded_files=[{"name": "secret.txt", "mime_type": "text/plain", "content_bytes": b"top secret"}],
    )

    assert message_id == 0
    assert "blocked" in error
    with session_scope() as session:
        assert session.query(Message).filter(Message.conversation_id == conversation_id).count() == 0
        assert session.query(File).count() == 0
    assert list(tmp_path.iterdir()) == []


def test_allowed_upload_persists_message_and_file(sqlite_db, monkeypatch, tmp_path):
    user_id = seed_user("upload-user")
    conversation_id = create_new_conversation(user_id)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(utils, "MS_DLP_AVAILABLE", False)

    message_id, error = add_message_to_conversation(
        conversation_id,
        "user",
        "hello",
        uploaded_files=[{"name": "notes.txt", "mime_type": "text/plain", "content_bytes": b"hello"}],
    )

    assert error is None and message_id > 0
    with session_scope() as session:
        stored = session.query(File).filter(File.message_id == message_id).one()
        assert stored.original_name == "notes.txt"
        # File contents are intentionally not retained after the DLP checks.
        assert stored.path is None
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# privacy_scanner: event logging and pattern thresholds
# ---------------------------------------------------------------------------

def test_anonymize_text_logs_exactly_one_event(sqlite_db):
    user_id = seed_user("anon-user", scan_enabled=True, scan_level="standard", auto_anonymize=True)

    anonymized, detected = privacy_scanner.anonymize_text(user_id, "contact me at jane@example.com")

    assert anonymized == "contact me at email@redacted.com"
    assert "email" in detected
    with session_scope() as session:
        events = session.query(DetectionEvent).filter(DetectionEvent.user_id == user_id).all()
        assert [event.action for event in events] == ["anonymize"]
        assert events[0].timestamp is not None  # DB default populated


def test_strict_low_confidence_patterns_are_detectable(sqlite_db):
    user_id = seed_user("strict-user", scan_enabled=True, scan_level="strict")

    found, detected = privacy_scanner.scan_text(user_id, "AFM 123456789", log_event=False)

    assert found is True
    assert "greek_tax_id" in detected


def test_email_pattern_does_not_accept_pipe_in_tld():
    regex = privacy_scanner.COMPILED_PATTERNS["email"]["regex"]
    assert regex.search("a@b.com")
    assert regex.search("a@b.c|m") is None or regex.search("a@b.c|m").group(0) == "a@b.c"


def test_get_detection_events_parses_json_string_patterns(sqlite_db):
    user_id = seed_user("json-user")
    with session_scope() as session:
        session.add(DetectionEvent(
            user_id=user_id,
            action="scan",
            severity="medium",
            detected_patterns=json.dumps({"email": ["a@b.com"]}),
        ))

    events = privacy_scanner.get_detection_events(user_id=user_id)

    assert events[0]["detected_patterns"] == {"email": ["a@b.com"]}


# ---------------------------------------------------------------------------
# message ordering
# ---------------------------------------------------------------------------

def test_conversation_messages_are_returned_in_chronological_order(sqlite_db):
    user_id = seed_user("order-user")
    conversation_id = create_new_conversation(user_id)
    base = datetime(2026, 1, 1, 12, 0, 0)
    with session_scope() as session:
        session.add(Message(conversation_id=conversation_id, role="assistant", content="second", timestamp=base + timedelta(minutes=1)))
        session.add(Message(conversation_id=conversation_id, role="user", content="first", timestamp=base))
        session.add(Message(conversation_id=conversation_id, role="user", content="third", timestamp=base + timedelta(minutes=2)))

    conversation = get_conversation(conversation_id, requesting_user_id=user_id)

    assert [m["content"] for m in conversation["messages"]] == ["first", "second", "third"]


def test_build_chat_ai_messages_history_window_uses_chronological_order():
    base = datetime(2026, 1, 1, 12, 0, 0)
    # Deliberately unsorted input with one more message than the window.
    messages = [
        {"id": 3, "role": "user", "content": "m3", "timestamp": base + timedelta(minutes=3)},
        {"id": 1, "role": "user", "content": "m1", "timestamp": base + timedelta(minutes=1)},
        {"id": 2, "role": "assistant", "content": "m2", "timestamp": base + timedelta(minutes=2)},
    ]

    result = build_chat_ai_messages("sys", messages, current_message_id=None, current_user_content="now", history_limit=2)

    assert [m["content"] for m in result] == ["sys", "m2", "m3", "now"]


# ---------------------------------------------------------------------------
# local model settings: zero is a valid value
# ---------------------------------------------------------------------------

def test_local_model_snapshot_preserves_zero_values():
    settings = SimpleNamespace(
        local_model_path="m.gguf",
        local_model_context_size=1024,
        local_model_gpu_layers=0,
        local_model_temperature=0.0,
        disable_scan_for_local_model=False,
    )

    snapshot = get_local_model_settings_snapshot(settings)

    assert snapshot["local_model_gpu_layers"] == 0
    assert snapshot["local_model_temperature"] == 0.0
    assert snapshot["disable_scan_for_local_model"] is False


# ---------------------------------------------------------------------------
# file_processor: text extraction for binary formats
# ---------------------------------------------------------------------------

def _build_office_zip(members):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, xml in members.items():
            archive.writestr(name, xml)
    return buffer.getvalue()


def test_extract_text_from_bytes_handles_plaintext_and_csv():
    assert file_processor.extract_text_from_bytes("a.txt", "text/plain", b"hello") == "hello"
    assert file_processor.extract_text_from_bytes("a.csv", "text/csv", b"a,b\n1,2\n") == "a,b\n1,2\n"
    # Latin-1 bytes must not blow up.
    assert "caf" in file_processor.extract_text_from_bytes("a.txt", "text/plain", "café".encode("latin-1"))


def test_extract_text_from_bytes_reads_pptx_slides_in_order():
    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    data = _build_office_zip({
        "ppt/slides/slide10.xml": f'<p:sld {ns} xmlns:p="x"><a:t>ten</a:t></p:sld>',
        "ppt/slides/slide2.xml": f'<p:sld {ns} xmlns:p="x"><a:t>two</a:t></p:sld>',
        "ppt/slides/slide1.xml": f'<p:sld {ns} xmlns:p="x"><a:t>one</a:t><a:t>SSN 123-45-6789</a:t></p:sld>',
    })

    text = file_processor.extract_text_from_bytes("deck.pptx", "application/octet-stream", data)

    assert text.split("\n") == ["one SSN 123-45-6789", "two", "ten"]


def test_extract_text_from_bytes_docx_fallback_without_python_docx(monkeypatch):
    monkeypatch.setattr(file_processor, "DOCX_AVAILABLE", False)
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    data = _build_office_zip({"word/document.xml": f"<w:document {ns}><w:t>card 4111111111111111</w:t></w:document>"})

    text = file_processor.extract_text_from_bytes(
        "doc.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        data,
    )

    assert text == "card 4111111111111111"


def test_build_file_payloads_extracts_text_from_binary_documents():
    class FakeUpload:
        def __init__(self, name, content_type, content):
            self.name = name
            self.type = content_type
            self._content = content

        def getvalue(self):
            return self._content

    ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
    pptx_bytes = _build_office_zip({"ppt/slides/slide1.xml": f'<p:sld {ns} xmlns:p="x"><a:t>hello slide</a:t></p:sld>'})

    payloads = build_file_payloads([FakeUpload("deck.pptx", None, pptx_bytes)])

    assert payloads[0]["content"] == "hello slide"
    assert payloads[0]["content_bytes"] == pptx_bytes


def test_scan_file_chunks_uses_extractor_for_small_binary_files(tmp_path, monkeypatch):
    pdf_path = tmp_path / "small.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 binary junk without the secret")

    def fake_pdf_extractor(file_obj, chunk_size=1000, overlap=0):
        yield "extracted text with mail@example.com"

    monkeypatch.setattr(file_processor, "extract_text_from_pdf", fake_pdf_extractor)
    seen = []

    def scanner(text):
        seen.append(text)
        return "mail@example.com" in text, {"email": ["mail@example.com"]} if "mail@example.com" in text else {}

    found, detected, _ = file_processor.scan_file_chunks(str(pdf_path), "application/pdf", scanner)

    assert found is True
    assert detected == {"email": ["mail@example.com"]}
    assert seen == ["extracted text with mail@example.com"]


def test_scan_file_chunks_fast_path_for_small_text_files(tmp_path):
    txt_path = tmp_path / "small.txt"
    txt_path.write_text("ssn 123-45-6789")

    found, detected, _ = file_processor.scan_file_chunks(str(txt_path), "text/plain", file_processor.demo_scan_chunk)

    assert found is True
    assert detected["ssn"] == ["123-45-6789"]


# ---------------------------------------------------------------------------
# azure_auth: stateless signed OAuth state
# ---------------------------------------------------------------------------

def test_signed_auth_state_round_trips_and_rejects_tampering(monkeypatch):
    monkeypatch.setenv("AZURE_STATE_SECRET", "unit-test-secret")

    state = azure_auth.generate_auth_state(now=1_000_000)

    assert azure_auth.verify_auth_state(state, now=1_000_100) is True
    assert azure_auth.verify_auth_state(state, now=1_000_000 + azure_auth.AUTH_STATE_MAX_AGE_SECONDS + 1) is False
    timestamp, nonce, signature = state.split(".")
    assert azure_auth.verify_auth_state(f"{timestamp}.{nonce}x.{signature}", now=1_000_100) is False
    assert azure_auth.verify_auth_state("not-a-state", now=1_000_100) is False
    assert azure_auth.verify_auth_state(None) is False


def test_process_auth_code_rejects_invalid_state(monkeypatch):
    called = {"msal": False}
    monkeypatch.setattr(azure_auth, "get_msal_app", lambda: called.__setitem__("msal", True))

    assert azure_auth.process_auth_code("code", "bogus.state.value") is False
    assert called["msal"] is False
