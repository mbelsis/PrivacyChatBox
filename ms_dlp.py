"""
Microsoft Purview / Information Protection integration.

Three real Microsoft mechanisms are used:

1. **Sensitivity labels read from file metadata (offline).**
   Purview-labelled Office files, PDFs and e-mails carry ``MSIP_Label_<GUID>_*``
   properties (``docProps/custom.xml``, ``docMetadata/LabelInfo.xml``, PDF XMP /
   document info, ``msip_labels`` e-mail header). Reading them locally means a file
   never has to leave the server just to learn its label.

2. **Label resolution through Microsoft Graph.**
   ``GET /beta/security/informationProtection/sensitivityLabels`` (application
   permission ``InformationProtectionPolicy.Read.All``) turns label GUIDs into
   display names, which are mapped to the application's sensitivity levels.

3. **Purview DLP policy evaluation through Microsoft Graph v1.0.**
   ``POST /v1.0/users/{id}/dataSecurityAndGovernance/processContent`` (application
   permission ``Content.Process.User``) evaluates prompts and file text against the
   tenant's DLP policies for this Entra application and returns the action to
   enforce. Blocks decided locally are recorded in Purview audit with
   ``POST /v1.0/users/{id}/dataSecurityAndGovernance/activities/contentActivities``
   (``ContentActivity.Write``).

Purview evaluation requires a Microsoft Entra user object ID, so it applies to users
who signed in with Azure AD. Label-based blocking applies to every user.
"""

import json
import logging
import os
import re
import threading
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import msal
import requests

from database import session_scope
from models import DetectionEvent, Settings, User

logger = logging.getLogger("ms_dlp")

GRAPH_ROOT = "https://graph.microsoft.com"
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]

# Network timeout (connect, read) for Microsoft Graph calls.
HTTP_TIMEOUT = (10, 30)

# Sensitivity levels in order of increasing sensitivity. User thresholds are stored
# as these keys in ``Settings.ms_dlp_sensitivity_threshold``.
SENSITIVITY_LEVELS = {
    "general": 0,
    "internal": 1,
    "confidential": 2,
    "highly_confidential": 3,
    "secret": 4,
    "top_secret": 5,
}

# Phrases recognised in label names, mapped to levels. A label name matching several
# phrases (e.g. "Confidential - Internal") takes the most sensitive match.
_LEVEL_PHRASES = [
    ("top secret", "top_secret"),
    ("highly confidential", "highly_confidential"),
    ("strictly confidential", "highly_confidential"),
    ("restricted", "highly_confidential"),
    ("secret", "secret"),
    ("confidential", "confidential"),
    ("internal", "internal"),
    ("general", "general"),
    ("public", "general"),
    ("personal", "general"),
    ("non-business", "general"),
]

_GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_MSIP_PROPERTY = re.compile(
    r"MSIP_Label_(" + _GUID + r")_(Enabled|Name|SiteId|Method|ContentBits|Removed)"
    # Separators never span a line break, so a closing XML tag cannot capture the next line.
    r"[ \t\"'=:>(]{1,8}([^;<)\"'\r\n]{0,200})"
)
_LABELINFO_NS = "{http://schemas.microsoft.com/office/2020/mipLabelMetadata}"

# Maximum bytes scanned when looking for label metadata in non-zip formats.
_MAX_METADATA_SCAN_BYTES = 8 * 1024 * 1024
# Maximum characters of text sent to Purview in one processContent call.
_MAX_PURVIEW_TEXT_CHARS = 100_000

_LABEL_CACHE: Dict[str, Any] = {"expires_at": 0.0, "labels": {}}
_LABEL_CACHE_TTL_SECONDS = 3600
_MSAL_APPS: Dict[Tuple[str, str], msal.ConfidentialClientApplication] = {}
_LOCK = threading.Lock()


# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------

def _env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_ms_settings() -> Dict[str, Any]:
    """Microsoft integration settings from the environment."""
    settings: Dict[str, Any] = {
        "MS_CLIENT_ID": os.environ.get("MS_CLIENT_ID", ""),
        "MS_CLIENT_SECRET": os.environ.get("MS_CLIENT_SECRET", ""),
        "MS_TENANT_ID": os.environ.get("MS_TENANT_ID", ""),
        # Entra application whose Purview DLP policies apply. Defaults to MS_CLIENT_ID.
        "MS_PURVIEW_APPLICATION_ID": os.environ.get("MS_PURVIEW_APPLICATION_ID") or os.environ.get("MS_CLIENT_ID", ""),
        "MS_PURVIEW_APP_NAME": os.environ.get("MS_PURVIEW_APP_NAME", "PrivacyChatBoX"),
        "purview_enabled": _env_flag("MS_PURVIEW_PROCESS_CONTENT", True),
        "fail_closed": _env_flag("MS_PURVIEW_FAIL_CLOSED", False),
    }
    missing = [key for key in ("MS_CLIENT_ID", "MS_CLIENT_SECRET", "MS_TENANT_ID") if not settings[key]]
    settings["is_configured"] = not missing
    settings["missing"] = missing
    if os.environ.get("MS_DLP_ENDPOINT_ID"):
        logger.info("MS_DLP_ENDPOINT_ID is no longer used and can be removed.")
    return settings


def _msal_app(settings: Dict[str, Any]) -> msal.ConfidentialClientApplication:
    key = (settings["MS_CLIENT_ID"], settings["MS_TENANT_ID"])
    with _LOCK:
        app = _MSAL_APPS.get(key)
        if app is None:
            app = msal.ConfidentialClientApplication(
                settings["MS_CLIENT_ID"],
                client_credential=settings["MS_CLIENT_SECRET"],
                authority=f"https://login.microsoftonline.com/{settings['MS_TENANT_ID']}",
            )
            _MSAL_APPS[key] = app
        return app


def get_ms_graph_token() -> Optional[str]:
    """App-only Microsoft Graph token (MSAL caches and refreshes it internally)."""
    settings = get_ms_settings()
    if not settings["is_configured"]:
        return None
    result = _msal_app(settings).acquire_token_for_client(scopes=GRAPH_SCOPE)
    if "access_token" in result:
        return result["access_token"]
    logger.error("Microsoft Graph token request failed: %s %s", result.get("error"), result.get("error_description"))
    return None


def _graph_request(method: str, path: str, token: str, **kwargs) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "client-request-id": str(uuid.uuid4()),
    }
    headers.update(kwargs.pop("headers", {}))
    return requests.request(method, f"{GRAPH_ROOT}{path}", headers=headers, timeout=HTTP_TIMEOUT, **kwargs)


# --------------------------------------------------------------------------------------
# 1. Label extraction from file metadata
# --------------------------------------------------------------------------------------

def _collect_msip_properties(text: str, labels: Dict[str, Dict[str, Any]], source: str) -> None:
    for guid, prop, raw_value in _MSIP_PROPERTY.findall(text):
        entry = labels.setdefault(guid.lower(), {"id": guid.lower(), "source": source})
        value = raw_value.strip()
        # XML closing tags (</...MSIP_Label_x_Name>) match with an empty value; never
        # let them erase a value captured from the opening tag.
        if value or prop.lower() not in entry:
            entry[prop.lower()] = value


def _labels_from_office_zip(archive: zipfile.ZipFile) -> Dict[str, Dict[str, Any]]:
    labels: Dict[str, Dict[str, Any]] = {}
    names = set(archive.namelist())

    if "docProps/custom.xml" in names:
        try:
            root = ET.fromstring(archive.read("docProps/custom.xml"))
            for prop in root:
                prop_name = prop.attrib.get("name", "")
                value = "".join(child.text or "" for child in prop)
                _collect_msip_properties(f"{prop_name}={value};", labels, "docProps/custom.xml")
        except ET.ParseError:
            pass

    if "docMetadata/LabelInfo.xml" in names:
        try:
            root = ET.fromstring(archive.read("docMetadata/LabelInfo.xml"))
            for node in root.iter(f"{_LABELINFO_NS}label"):
                guid = node.attrib.get("id", "").strip("{}").lower()
                if not re.fullmatch(_GUID, guid):
                    continue
                entry = labels.setdefault(guid, {"id": guid, "source": "docMetadata/LabelInfo.xml"})
                entry["enabled"] = "true" if node.attrib.get("enabled") in {"1", "true"} else "false"
                entry["removed"] = "true" if node.attrib.get("removed") in {"1", "true"} else "false"
                entry["method"] = node.attrib.get("method", "")
                entry["siteid"] = node.attrib.get("siteId", "").strip("{}")
        except ET.ParseError:
            pass

    return labels


def extract_sensitivity_labels(file_path: str) -> List[Dict[str, Any]]:
    """
    Return the active sensitivity labels embedded in a file.

    Each label is a dict with ``id`` (GUID) and, when present in the metadata,
    ``name``, ``method`` and ``siteid``. Removed or disabled labels are ignored.
    """
    labels: Dict[str, Dict[str, Any]] = {}
    try:
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path) as archive:
                labels = _labels_from_office_zip(archive)
        else:
            with open(file_path, "rb") as handle:
                data = handle.read(_MAX_METADATA_SCAN_BYTES)
            # PDF XMP / info dictionary and RFC 822 headers are ASCII-compatible;
            # Outlook .msg files store properties as UTF-16LE.
            _collect_msip_properties(data.decode("latin-1"), labels, "embedded metadata")
            for offset in (0, 1):
                _collect_msip_properties(data[offset:].decode("utf-16-le", errors="ignore"), labels, "embedded metadata")
    except (OSError, zipfile.BadZipFile) as exc:
        logger.warning("Unable to read sensitivity label metadata from %s: %s", file_path, exc)
        return []

    active = []
    for label in labels.values():
        if label.get("enabled", "true").lower() != "true":
            continue
        if label.get("removed", "false").lower() == "true":
            continue
        active.append(label)
    return active


# --------------------------------------------------------------------------------------
# 2. Label resolution and classification
# --------------------------------------------------------------------------------------

def get_tenant_sensitivity_labels(force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Tenant label catalogue keyed by lowercase GUID (cached for an hour)."""
    now = time.time()
    with _LOCK:
        if not force_refresh and _LABEL_CACHE["expires_at"] > now:
            return _LABEL_CACHE["labels"]

    labels: Dict[str, Dict[str, Any]] = {}
    token = get_ms_graph_token()
    if token:
        try:
            response = _graph_request("GET", "/beta/security/informationProtection/sensitivityLabels", token)
            if response.status_code == 200:
                for item in response.json().get("value", []):
                    labels[str(item.get("id", "")).lower()] = {
                        "id": str(item.get("id", "")).lower(),
                        "name": item.get("displayName") or item.get("name") or "",
                        "sensitivity": item.get("sensitivity"),
                    }
            else:
                logger.warning("Listing sensitivity labels failed: %s %s", response.status_code, response.text[:300])
        except requests.RequestException as exc:
            logger.warning("Listing sensitivity labels failed: %s", exc)

    with _LOCK:
        _LABEL_CACHE["labels"] = labels
        # Retry sooner after a failure so a transient outage does not stick for an hour.
        _LABEL_CACHE["expires_at"] = now + (_LABEL_CACHE_TTL_SECONDS if labels else 300)
    return labels


def _configured_label_levels() -> Dict[str, str]:
    raw = os.environ.get("MS_DLP_LABEL_LEVELS", "").strip()
    if not raw:
        return {}
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("MS_DLP_LABEL_LEVELS is not valid JSON; ignoring it.")
        return {}
    return {
        str(key).strip().lower(): str(value).strip().lower()
        for key, value in mapping.items()
        if str(value).strip().lower() in SENSITIVITY_LEVELS
    }


def classify_label_level(label: Dict[str, Any]) -> str:
    """
    Map a label to one of :data:`SENSITIVITY_LEVELS`.

    Order: explicit ``MS_DLP_LABEL_LEVELS`` mapping (by GUID or name), then phrases in
    the label name, then ``MS_DLP_UNKNOWN_LABEL_LEVEL`` (default ``confidential``,
    i.e. unknown labels are treated as sensitive rather than ignored).
    """
    overrides = _configured_label_levels()
    label_id = str(label.get("id", "")).lower()
    name = str(label.get("name", "") or "")
    for key in (label_id, name.lower()):
        if key and key in overrides:
            return overrides[key]

    normalized = re.sub(r"\s+", " ", re.sub(r"[_\\/|]+", " ", name.lower())).strip()
    matches = [level for phrase, level in _LEVEL_PHRASES if phrase in normalized]
    if matches:
        return max(matches, key=lambda level: SENSITIVITY_LEVELS[level])

    fallback = os.environ.get("MS_DLP_UNKNOWN_LABEL_LEVEL", "confidential").strip().lower()
    return fallback if fallback in SENSITIVITY_LEVELS else "confidential"


def resolve_file_labels(file_path: str) -> List[Dict[str, Any]]:
    """Extract a file's labels and annotate each with ``name`` and ``level``."""
    labels = extract_sensitivity_labels(file_path)
    if not labels:
        return []
    tenant_labels = get_tenant_sensitivity_labels() if any(not label.get("name") for label in labels) else {}
    for label in labels:
        if not label.get("name"):
            label["name"] = tenant_labels.get(label["id"], {}).get("name", "")
        label["level"] = classify_label_level(label)
    return labels


def check_sensitivity_label(file_path: str, file_mime: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Backwards-compatible helper: return ``(False, most_sensitive_label)``.

    The threshold comparison happens in :func:`scan_file_for_sensitivity`, which knows
    the user's configured threshold.
    """
    labels = resolve_file_labels(file_path)
    if not labels:
        return False, None
    return False, max(labels, key=lambda label: SENSITIVITY_LEVELS[label["level"]])


# --------------------------------------------------------------------------------------
# 3. Purview DLP evaluation (processContent) and audit (contentActivities)
# --------------------------------------------------------------------------------------

@dataclass
class PurviewDecision:
    allowed: bool = True
    evaluated: bool = False
    restriction: Optional[str] = None  # "block", "warn" or "audit"
    errors: List[str] = field(default_factory=list)

    @property
    def warn(self) -> bool:
        return self.restriction == "warn"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def build_purview_request(
    text: Optional[str],
    content_name: str,
    activity: str,
    settings: Dict[str, Any],
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a ``processContentRequest`` body (also used for contentActivities)."""
    now = _iso_now()
    entry: Dict[str, Any] = {
        "@odata.type": "microsoft.graph.processConversationMetadata",
        "identifier": str(uuid.uuid4()),
        "name": content_name,
        "correlationId": correlation_id or str(uuid.uuid4()),
        "sequenceNumber": 0,
        "isTruncated": False,
        "createdDateTime": now,
        "modifiedDateTime": now,
    }
    if text is not None:
        truncated = text[:_MAX_PURVIEW_TEXT_CHARS]
        entry["content"] = {"@odata.type": "microsoft.graph.textContent", "data": truncated}
        entry["isTruncated"] = len(truncated) < len(text)
        entry["length"] = len(text.encode("utf-8"))

    app_metadata = {"name": settings["MS_PURVIEW_APP_NAME"], "version": "1.0"}
    return {
        "contentToProcess": {
            "contentEntries": [entry],
            "activityMetadata": {"activity": activity},
            "deviceMetadata": {"deviceType": "Unmanaged"},
            "protectedAppMetadata": {
                **app_metadata,
                "applicationLocation": {
                    "@odata.type": "microsoft.graph.policyLocationApplication",
                    "value": settings["MS_PURVIEW_APPLICATION_ID"],
                },
            },
            "integratedAppMetadata": app_metadata,
        }
    }


def parse_purview_response(payload: Dict[str, Any]) -> PurviewDecision:
    """Translate a ``processContentResponse`` into an enforcement decision."""
    decision = PurviewDecision(evaluated=True)
    restrictions = [
        str(action.get("restrictionAction", "")).lower()
        for action in payload.get("policyActions") or []
        if str(action.get("action", "")).lower() == "restrictaccess"
    ]
    for level in ("block", "warn", "audit"):
        if level in restrictions:
            decision.restriction = level
            break
    decision.allowed = decision.restriction != "block"
    decision.errors = [
        str(error.get("message") or error.get("errorType") or error)
        for error in payload.get("processingErrors") or []
    ]
    return decision


def get_entra_object_id(user_id: int) -> Optional[str]:
    """Microsoft Entra object ID for a local user (set when they sign in with Azure AD)."""
    with session_scope() as session:
        row = session.query(User.azure_id).filter(User.id == user_id).first()
        return row[0] if row and row[0] else None


def evaluate_with_purview(user_id: int, text: str, content_name: str, activity: str = "uploadText") -> PurviewDecision:
    """
    Evaluate content against the tenant's Purview DLP policies.

    Returns an "allowed, not evaluated" decision when Purview evaluation does not
    apply (not configured, disabled, or a local account without an Entra identity).
    Errors fail open unless ``MS_PURVIEW_FAIL_CLOSED=true``.
    """
    settings = get_ms_settings()
    if not (settings["is_configured"] and settings["purview_enabled"]) or not text:
        return PurviewDecision()

    entra_id = get_entra_object_id(user_id)
    if not entra_id:
        return PurviewDecision()

    failure = PurviewDecision(allowed=not settings["fail_closed"])
    token = get_ms_graph_token()
    if not token:
        failure.errors.append("Unable to obtain a Microsoft Graph token.")
        return failure

    body = build_purview_request(text, content_name, activity, settings)
    try:
        response = _graph_request(
            "POST", f"/v1.0/users/{entra_id}/dataSecurityAndGovernance/processContent", token, json=body
        )
    except requests.RequestException as exc:
        failure.errors.append(f"Purview request failed: {exc}")
        logger.error(failure.errors[-1])
        return failure

    if response.status_code != 200:
        failure.errors.append(f"Purview processContent returned {response.status_code}: {response.text[:300]}")
        logger.error(failure.errors[-1])
        return failure

    decision = parse_purview_response(response.json())
    for error in decision.errors:
        logger.warning("Purview processing error: %s", error)
    return decision


def record_purview_activity(user_id: int, content_name: str, activity: str = "uploadFile") -> bool:
    """Record an activity in Purview audit (no content is sent). Best effort."""
    settings = get_ms_settings()
    entra_id = get_entra_object_id(user_id) if settings["is_configured"] else None
    if not entra_id:
        return False
    token = get_ms_graph_token()
    if not token:
        return False
    body = build_purview_request(None, content_name, activity, settings)
    try:
        response = _graph_request(
            "POST", f"/v1.0/users/{entra_id}/dataSecurityAndGovernance/activities/contentActivities", token, json=body
        )
    except requests.RequestException as exc:
        logger.warning("Recording Purview content activity failed: %s", exc)
        return False
    if response.status_code not in (200, 201, 204):
        logger.warning("Recording Purview content activity failed: %s %s", response.status_code, response.text[:300])
        return False
    return True


def _log_block_event(user_id: int, action: str, details: Dict[str, List[Any]], file_name: str = "") -> None:
    try:
        with session_scope() as session:
            session.add(DetectionEvent(
                user_id=user_id,
                action=action,
                severity="high",
                detected_patterns=details,
                file_names=file_name,
            ))
    except Exception as exc:
        logger.error("Unable to log DLP block event: %s", exc)


# --------------------------------------------------------------------------------------
# Public entry points used by the application
# --------------------------------------------------------------------------------------

def is_dlp_integration_enabled(user_id: int) -> bool:
    """DLP is active when Microsoft credentials are configured and the user has it enabled."""
    if not get_ms_settings()["is_configured"]:
        return False
    with session_scope() as session:
        row = session.query(Settings.enable_ms_dlp).filter(Settings.user_id == user_id).first()
    return True if row is None or row[0] is None else bool(row[0])


def get_user_threshold(user_id: int) -> str:
    with session_scope() as session:
        row = session.query(Settings.ms_dlp_sensitivity_threshold).filter(Settings.user_id == user_id).first()
    threshold = (row[0] if row and row[0] else "confidential").lower()
    return threshold if threshold in SENSITIVITY_LEVELS else "confidential"


def scan_file_for_sensitivity(
    user_id: int,
    file_path: str,
    file_name: str,
    file_mime: Optional[str] = None,
    file_text: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Decide whether an uploaded file may be used.

    1. Block when an embedded sensitivity label is at or above the user's threshold.
    2. Otherwise, for Entra users, evaluate the file's text with Purview DLP.

    Returns ``(allowed, error_message)``.
    """
    if not is_dlp_integration_enabled(user_id):
        return True, None

    threshold = get_user_threshold(user_id)
    labels = resolve_file_labels(file_path)
    blocking = [
        label for label in labels
        if SENSITIVITY_LEVELS[label["level"]] >= SENSITIVITY_LEVELS[threshold]
    ]
    if blocking:
        label = max(blocking, key=lambda item: SENSITIVITY_LEVELS[item["level"]])
        label_name = label.get("name") or label["id"]
        _log_block_event(
            user_id,
            "block_sensitive_file",
            {"sensitivity_label": [f"{label_name} ({label['level']})"]},
            file_name,
        )
        record_purview_activity(user_id, file_name, "uploadFile")
        return False, (
            f"File blocked due to Microsoft sensitivity label: {label_name}. "
            f"Files labelled '{label['level'].replace('_', ' ')}' or higher cannot be uploaded."
        )

    if file_text is None:
        try:
            from file_processor import extract_text_from_bytes
            with open(file_path, "rb") as handle:
                file_text = extract_text_from_bytes(file_name, file_mime, handle.read())
        except Exception as exc:
            logger.warning("Unable to extract text for Purview evaluation of %s: %s", file_name, exc)
            file_text = None

    if file_text:
        decision = evaluate_with_purview(user_id, file_text, file_name, "uploadFile")
        if not decision.allowed:
            _log_block_event(
                user_id,
                "block_dlp_policy",
                {"purview_dlp_policy": [decision.restriction or "error"]},
                file_name,
            )
            return False, f"File blocked by your organisation's Microsoft Purview DLP policy: {file_name}."

    return True, None


def check_prompt_with_purview(user_id: int, text: str) -> Tuple[bool, Optional[str]]:
    """
    Evaluate a chat prompt against Purview DLP before it is sent to an AI model.

    Returns ``(allowed, message)``; ``message`` is set for blocks and warnings.
    """
    if not is_dlp_integration_enabled(user_id):
        return True, None
    decision = evaluate_with_purview(user_id, text, "PrivacyChatBoX chat prompt", "uploadText")
    if not decision.allowed:
        _log_block_event(user_id, "block_dlp_policy", {"purview_dlp_policy": [decision.restriction or "error"]})
        return False, "This message was blocked by your organisation's Microsoft Purview DLP policy."
    if decision.warn:
        return True, "Your organisation's Microsoft Purview DLP policy flagged this message as sensitive."
    return True, None
