"""Tests for the Microsoft Purview / Information Protection integration."""

import io
import zipfile

import pytest

import ms_dlp
import utils
from database import session_scope
from models import DetectionEvent, File, Message, Settings, User
from utils import add_message_to_conversation, create_new_conversation

LABEL_ID = "0b5c0b2a-6f7e-4c2b-9d1e-2a3b4c5d6e7f"
SITE_ID = "11111111-2222-3333-4444-555555555555"


def make_docx_with_custom_label(name="Highly Confidential", enabled="true"):
    custom_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
            xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="2" name="MSIP_Label_{LABEL_ID}_Enabled"><vt:lpwstr>{enabled}</vt:lpwstr></property>
  <property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="3" name="MSIP_Label_{LABEL_ID}_Name"><vt:lpwstr>{name}</vt:lpwstr></property>
  <property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="4" name="MSIP_Label_{LABEL_ID}_SiteId"><vt:lpwstr>{SITE_ID}</vt:lpwstr></property>
</Properties>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document xmlns:w='x'/>")
        archive.writestr("docProps/custom.xml", custom_xml)
    return buffer.getvalue()


def make_docx_with_labelinfo(removed="0"):
    label_info = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<clbl:labelList xmlns:clbl="http://schemas.microsoft.com/office/2020/mipLabelMetadata">
  <clbl:label id="{{{LABEL_ID}}}" enabled="1" method="Privileged" siteId="{{{SITE_ID}}}" removed="{removed}"/>
</clbl:labelList>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("docMetadata/LabelInfo.xml", label_info)
    return buffer.getvalue()


@pytest.fixture
def ms_configured(monkeypatch):
    monkeypatch.setenv("MS_CLIENT_ID", "app-id")
    monkeypatch.setenv("MS_CLIENT_SECRET", "secret")
    monkeypatch.setenv("MS_TENANT_ID", "tenant-id")
    monkeypatch.delenv("MS_DLP_LABEL_LEVELS", raising=False)
    monkeypatch.delenv("MS_DLP_UNKNOWN_LABEL_LEVEL", raising=False)
    monkeypatch.delenv("MS_PURVIEW_FAIL_CLOSED", raising=False)
    monkeypatch.setattr(ms_dlp, "get_ms_graph_token", lambda: "token")
    monkeypatch.setattr(ms_dlp, "get_tenant_sensitivity_labels", lambda force_refresh=False: {})
    monkeypatch.setattr(ms_dlp, "record_purview_activity", lambda *args, **kwargs: True)


def seed_user(username, azure_id=None, threshold="confidential"):
    with session_scope() as session:
        user = User(username=username, password="hash", role="user", azure_id=azure_id)
        session.add(user)
        session.flush()
        session.add(Settings(user_id=user.id, enable_ms_dlp=True, ms_dlp_sensitivity_threshold=threshold))
        return user.id


# ---------------------------------------------------------------------------
# Label extraction
# ---------------------------------------------------------------------------

def test_extracts_label_from_office_custom_properties(tmp_path):
    path = tmp_path / "doc.docx"
    path.write_bytes(make_docx_with_custom_label())

    labels = ms_dlp.extract_sensitivity_labels(str(path))

    assert len(labels) == 1
    assert labels[0]["id"] == LABEL_ID
    assert labels[0]["name"] == "Highly Confidential"
    assert labels[0]["siteid"] == SITE_ID


def test_disabled_label_is_ignored(tmp_path):
    path = tmp_path / "doc.docx"
    path.write_bytes(make_docx_with_custom_label(enabled="false"))
    assert ms_dlp.extract_sensitivity_labels(str(path)) == []


def test_extracts_label_from_labelinfo_and_ignores_removed(tmp_path):
    active = tmp_path / "active.docx"
    active.write_bytes(make_docx_with_labelinfo())
    removed = tmp_path / "removed.docx"
    removed.write_bytes(make_docx_with_labelinfo(removed="1"))

    labels = ms_dlp.extract_sensitivity_labels(str(active))

    assert [label["id"] for label in labels] == [LABEL_ID]
    assert labels[0]["method"] == "Privileged"
    assert ms_dlp.extract_sensitivity_labels(str(removed)) == []


def test_extracts_label_from_pdf_xmp_without_closing_tag_erasing_name(tmp_path):
    xmp = (
        f"<pdfx:MSIP_Label_{LABEL_ID}_Enabled>true</pdfx:MSIP_Label_{LABEL_ID}_Enabled>\n"
        f"<pdfx:MSIP_Label_{LABEL_ID}_Name>Secret</pdfx:MSIP_Label_{LABEL_ID}_Name>\n"
    )
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.7\n" + xmp.encode("ascii") + b"\n%%EOF")

    labels = ms_dlp.extract_sensitivity_labels(str(path))

    assert labels and labels[0]["name"] == "Secret"


def test_extracts_label_from_email_header_and_utf16_msg(tmp_path):
    header = f"msip_labels: MSIP_Label_{LABEL_ID}_Enabled=true; MSIP_Label_{LABEL_ID}_Name=Confidential;"
    eml = tmp_path / "mail.eml"
    eml.write_text(header + "\r\nSubject: hi\r\n\r\nbody")
    msg = tmp_path / "mail.msg"
    msg.write_bytes(b"\xd0\xcf\x11\xe0\x00" + header.encode("utf-16-le"))

    assert ms_dlp.extract_sensitivity_labels(str(eml))[0]["name"] == "Confidential"
    assert ms_dlp.extract_sensitivity_labels(str(msg))[0]["name"] == "Confidential"


def test_unlabelled_files_have_no_labels(tmp_path):
    path = tmp_path / "plain.txt"
    path.write_text("nothing to see")
    assert ms_dlp.extract_sensitivity_labels(str(path)) == []


# ---------------------------------------------------------------------------
# Level classification
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, level", [
    ("Public", "general"),
    ("General", "general"),
    ("Internal Only", "internal"),
    ("Confidential\\All Employees", "confidential"),
    ("Confidential - Internal", "confidential"),
    ("Highly Confidential", "highly_confidential"),
    ("Highly Confidential/Project X", "highly_confidential"),
    ("Secret", "secret"),
    ("Top Secret", "top_secret"),
])
def test_classify_label_level_by_name(monkeypatch, name, level):
    monkeypatch.delenv("MS_DLP_LABEL_LEVELS", raising=False)
    assert ms_dlp.classify_label_level({"id": LABEL_ID, "name": name}) == level


def test_classify_label_level_overrides_and_unknown_default(monkeypatch):
    monkeypatch.setenv("MS_DLP_LABEL_LEVELS", f'{{"{LABEL_ID}": "top_secret", "Project Falcon": "secret"}}')
    assert ms_dlp.classify_label_level({"id": LABEL_ID, "name": "General"}) == "top_secret"
    assert ms_dlp.classify_label_level({"id": "x", "name": "Project Falcon"}) == "secret"

    monkeypatch.delenv("MS_DLP_LABEL_LEVELS")
    assert ms_dlp.classify_label_level({"id": "x", "name": "Project Falcon"}) == "confidential"
    monkeypatch.setenv("MS_DLP_UNKNOWN_LABEL_LEVEL", "general")
    assert ms_dlp.classify_label_level({"id": "x", "name": ""}) == "general"


def test_resolve_file_labels_uses_graph_names_when_metadata_has_none(tmp_path, monkeypatch):
    path = tmp_path / "doc.docx"
    path.write_bytes(make_docx_with_labelinfo())
    monkeypatch.setattr(
        ms_dlp,
        "get_tenant_sensitivity_labels",
        lambda force_refresh=False: {LABEL_ID: {"id": LABEL_ID, "name": "Highly Confidential"}},
    )

    labels = ms_dlp.resolve_file_labels(str(path))

    assert labels[0]["name"] == "Highly Confidential"
    assert labels[0]["level"] == "highly_confidential"


# ---------------------------------------------------------------------------
# Purview request / response
# ---------------------------------------------------------------------------

def test_build_purview_request_matches_graph_contract(monkeypatch):
    monkeypatch.setenv("MS_CLIENT_ID", "app-guid")
    settings = ms_dlp.get_ms_settings()

    body = ms_dlp.build_purview_request("x" * 200_005, "Chat prompt", "uploadText", settings)

    request = body["contentToProcess"]
    entry = request["contentEntries"][0]
    assert entry["@odata.type"] == "microsoft.graph.processConversationMetadata"
    assert entry["content"]["@odata.type"] == "microsoft.graph.textContent"
    assert entry["isTruncated"] is True and len(entry["content"]["data"]) == 100_000
    assert {"identifier", "name", "createdDateTime", "modifiedDateTime"} <= set(entry)
    assert request["activityMetadata"] == {"activity": "uploadText"}
    assert request["protectedAppMetadata"]["applicationLocation"] == {
        "@odata.type": "microsoft.graph.policyLocationApplication",
        "value": "app-guid",
    }
    assert "deviceMetadata" in request and "integratedAppMetadata" in request

    audit = ms_dlp.build_purview_request(None, "file.docx", "uploadFile", settings)
    assert "content" not in audit["contentToProcess"]["contentEntries"][0]


def test_parse_purview_response_block_warn_and_allow():
    block = ms_dlp.parse_purview_response({
        "protectionScopeState": "notModified",
        "policyActions": [{"@odata.type": "#microsoft.graph.restrictAccessAction", "action": "restrictAccess", "restrictionAction": "block"}],
        "processingErrors": [],
    })
    warn = ms_dlp.parse_purview_response({"policyActions": [{"action": "restrictAccess", "restrictionAction": "warn"}]})
    allow = ms_dlp.parse_purview_response({"policyActions": [], "processingErrors": [{"errorType": "transient", "message": "x"}]})

    assert (block.allowed, block.restriction) == (False, "block")
    assert (warn.allowed, warn.warn) == (True, True)
    assert (allow.allowed, allow.restriction, allow.errors) == (True, None, ["x"])


def test_purview_not_evaluated_for_local_accounts(sqlite_db, ms_configured, monkeypatch):
    user_id = seed_user("local-user")
    monkeypatch.setattr(ms_dlp, "_graph_request", lambda *a, **k: pytest.fail("Graph must not be called"))

    decision = ms_dlp.evaluate_with_purview(user_id, "ssn 123-45-6789", "prompt")

    assert decision.allowed is True and decision.evaluated is False


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_prompt_blocked_by_purview_for_entra_user(sqlite_db, ms_configured, monkeypatch):
    user_id = seed_user("entra-user", azure_id="5def8f26-aff8-4db6-a08c-0fcf8f1aa2ba")
    calls = []

    def fake_graph(method, path, token, **kwargs):
        calls.append((method, path, kwargs["json"]))
        return FakeResponse(200, {"policyActions": [{"action": "restrictAccess", "restrictionAction": "block"}]})

    monkeypatch.setattr(ms_dlp, "_graph_request", fake_graph)

    allowed, message = ms_dlp.check_prompt_with_purview(user_id, "card 4532667785213500")

    assert allowed is False and "Purview" in message
    assert calls[0][1] == "/v1.0/users/5def8f26-aff8-4db6-a08c-0fcf8f1aa2ba/dataSecurityAndGovernance/processContent"
    with session_scope() as session:
        assert [e.action for e in session.query(DetectionEvent).all()] == ["block_dlp_policy"]


def test_purview_errors_fail_open_by_default_and_closed_when_configured(sqlite_db, ms_configured, monkeypatch):
    user_id = seed_user("entra-user2", azure_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    monkeypatch.setattr(ms_dlp, "_graph_request", lambda *a, **k: FakeResponse(503, text="unavailable"))

    assert ms_dlp.evaluate_with_purview(user_id, "hello", "prompt").allowed is True
    monkeypatch.setenv("MS_PURVIEW_FAIL_CLOSED", "true")
    assert ms_dlp.evaluate_with_purview(user_id, "hello", "prompt").allowed is False


# ---------------------------------------------------------------------------
# File enforcement end to end
# ---------------------------------------------------------------------------

def test_labelled_file_above_threshold_is_blocked_and_logged(sqlite_db, ms_configured, tmp_path):
    user_id = seed_user("label-user", threshold="confidential")
    path = tmp_path / "doc.docx"
    path.write_bytes(make_docx_with_custom_label("Highly Confidential"))

    allowed, error = ms_dlp.scan_file_for_sensitivity(user_id, str(path), "doc.docx")

    assert allowed is False
    assert "Highly Confidential" in error
    with session_scope() as session:
        event = session.query(DetectionEvent).one()
        assert (event.action, event.file_names) == ("block_sensitive_file", "doc.docx")


def test_labelled_file_below_threshold_is_allowed(sqlite_db, ms_configured, tmp_path):
    user_id = seed_user("label-user2", threshold="secret")
    path = tmp_path / "doc.docx"
    path.write_bytes(make_docx_with_custom_label("Confidential"))

    assert ms_dlp.scan_file_for_sensitivity(user_id, str(path), "doc.docx") == (True, None)


def test_dlp_disabled_without_credentials(sqlite_db, monkeypatch, tmp_path):
    for key in ("MS_CLIENT_ID", "MS_CLIENT_SECRET", "MS_TENANT_ID"):
        monkeypatch.delenv(key, raising=False)
    user_id = seed_user("no-creds")
    path = tmp_path / "doc.docx"
    path.write_bytes(make_docx_with_custom_label("Top Secret"))

    assert ms_dlp.is_dlp_integration_enabled(user_id) is False
    assert ms_dlp.scan_file_for_sensitivity(user_id, str(path), "doc.docx") == (True, None)


def test_anonymized_upload_cannot_bypass_label_check(sqlite_db, ms_configured, monkeypatch):
    """Anonymization rewrites file bytes as plain text; the label check must use the original."""
    monkeypatch.setattr(utils, "MS_DLP_AVAILABLE", True)
    monkeypatch.setattr(utils, "is_dlp_integration_enabled", ms_dlp.is_dlp_integration_enabled, raising=False)
    monkeypatch.setattr(utils, "scan_file_for_sensitivity", ms_dlp.scan_file_for_sensitivity, raising=False)
    user_id = seed_user("bypass-user")
    conversation_id = create_new_conversation(user_id)
    labelled = make_docx_with_custom_label("Highly Confidential")

    message_id, error = add_message_to_conversation(
        conversation_id,
        "user",
        "summarise this",
        uploaded_files=[{
            "name": "contract.docx",
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "content_bytes": b"anonymized plain text [REDACTED NAME]",
            "original_bytes": labelled,
            "text": "anonymized plain text [REDACTED NAME]",
        }],
    )

    assert message_id == 0 and "Highly Confidential" in error
    with session_scope() as session:
        assert session.query(Message).count() == 0


def test_allowed_uploads_are_not_retained_on_disk(sqlite_db, monkeypatch, tmp_path):
    import tempfile as tempfile_module

    monkeypatch.setattr(tempfile_module, "tempdir", str(tmp_path))
    monkeypatch.setattr(utils, "MS_DLP_AVAILABLE", False)
    user_id = seed_user("retention-user")
    conversation_id = create_new_conversation(user_id)

    message_id, error = add_message_to_conversation(
        conversation_id, "user", "hi",
        uploaded_files=[{"name": "a.txt", "mime_type": "text/plain", "content_bytes": b"hello"}],
    )

    assert error is None and message_id > 0
    assert list(tmp_path.iterdir()) == []
    with session_scope() as session:
        stored = session.query(File).one()
        assert (stored.original_name, stored.path, stored.size) == ("a.txt", None, 5)
