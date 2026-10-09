"""
Data-protection primitives: field-level encryption at rest and value masking.

Encryption at rest
------------------
Columns declared as :class:`EncryptedText` are encrypted with Fernet (AES-128-CBC +
HMAC-SHA256, from the ``cryptography`` package) before they reach the database.

* Keys come from ``DATA_ENCRYPTION_KEY``: one or more comma-separated Fernet keys.
  The first key encrypts; every key is tried for decryption, which allows rotation
  (prepend a new key, run ``migration_secure_existing_data.py``, then drop the old one).
* Without a key, values are stored as before (plaintext) and a warning is logged, so
  existing deployments keep working until a key is configured.
* Values written before encryption was enabled are read transparently and encrypted
  in place by ``migration_secure_existing_data.py``.

Generate a key with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Masking
-------
:func:`mask_value` reduces detected sensitive values to a non-identifying preview
(last four characters) before they are written to audit logs.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.types import Text, TypeDecorator

logger = logging.getLogger("data_protection")

ENCRYPTED_PREFIX = "enc:v1:"
UNREADABLE_PLACEHOLDER = "[encrypted content - unavailable]"

_warned_missing_key = False


def _load_keys() -> List[str]:
    raw = os.environ.get("DATA_ENCRYPTION_KEY", "")
    return [key.strip() for key in raw.split(",") if key.strip()]


def get_cipher():
    """Return a ``MultiFernet`` for the configured keys, or ``None`` when encryption is off."""
    global _warned_missing_key
    keys = _load_keys()
    if not keys:
        if not _warned_missing_key:
            logger.warning(
                "DATA_ENCRYPTION_KEY is not set: conversation content is stored unencrypted. "
                "Set it to enable encryption at rest."
            )
            _warned_missing_key = True
        return None
    from cryptography.fernet import Fernet, MultiFernet

    return MultiFernet([Fernet(key.encode("ascii")) for key in keys])


def encryption_enabled() -> bool:
    return bool(_load_keys())


def is_encrypted(value: Optional[str]) -> bool:
    return isinstance(value, str) and value.startswith(ENCRYPTED_PREFIX)


def encrypt_value(value: Optional[str]) -> Optional[str]:
    """Encrypt a string (no-op for ``None``, already-encrypted values, or no key)."""
    if value is None or is_encrypted(value):
        return value
    cipher = get_cipher()
    if cipher is None:
        return value
    return ENCRYPTED_PREFIX + cipher.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_value(value: Optional[str]) -> Optional[str]:
    """Decrypt a stored value; plaintext legacy values are returned unchanged."""
    if not is_encrypted(value):
        return value
    cipher = get_cipher()
    if cipher is None:
        logger.error("Encrypted data found but DATA_ENCRYPTION_KEY is not configured.")
        return UNREADABLE_PLACEHOLDER
    from cryptography.fernet import InvalidToken

    try:
        return cipher.decrypt(value[len(ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error("Unable to decrypt a stored value: wrong or rotated-out DATA_ENCRYPTION_KEY.")
        return UNREADABLE_PLACEHOLDER


def rotate_value(value: Optional[str]) -> Optional[str]:
    """Re-encrypt with the primary key (encrypts plaintext values too)."""
    if value is None:
        return None
    cipher = get_cipher()
    if cipher is None:
        return value
    if is_encrypted(value):
        token = value[len(ENCRYPTED_PREFIX):].encode("ascii")
        return ENCRYPTED_PREFIX + cipher.rotate(token).decode("ascii")
    return encrypt_value(value)


class EncryptedText(TypeDecorator):
    """Text column transparently encrypted at rest when ``DATA_ENCRYPTION_KEY`` is set."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        return decrypt_value(value)


# --------------------------------------------------------------------------------------
# Masking for audit logs
# --------------------------------------------------------------------------------------

def mask_value(value: Any, visible: int = 4, max_length: int = 40) -> str:
    """
    Mask a detected sensitive value for storage in audit logs.

    Letters and digits are replaced with ``*`` except the last ``visible`` alphanumeric
    characters; separators are kept so the shape stays recognisable
    (``123-45-6789`` -> ``***-**-6789``). Short values are fully masked. The function
    is idempotent, so already-masked values are unchanged.
    """
    text = str(value)[:max_length]
    # "*" counts as a maskable position so re-masking a masked value is a no-op.
    maskable = [index for index, char in enumerate(text) if char.isalnum() or char == "*"]
    keep = set(maskable[-visible:]) if len(maskable) > visible * 2 else set()
    return "".join(
        char if (not char.isalnum() or index in keep) else "*"
        for index, char in enumerate(text)
    )


def mask_detected_patterns(detected: Dict[str, List[Any]]) -> Dict[str, List[str]]:
    """Mask every match in a ``{pattern_type: [matches]}`` mapping, de-duplicated."""
    masked: Dict[str, List[str]] = {}
    for pattern_type, matches in (detected or {}).items():
        values = matches if isinstance(matches, list) else [matches]
        masked[pattern_type] = list(dict.fromkeys(mask_value(match) for match in values))
    return masked
