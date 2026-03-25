import base64
import hashlib
import hmac
import os
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime, timezone

PBKDF2_ITERATIONS = 600_000
PBKDF2_SCHEME = "pbkdf2_sha256"


def _hash_password_pbkdf2(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return (
        f"{PBKDF2_SCHEME}${iterations}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(digest).decode('ascii')}"
    )


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    return _hash_password_pbkdf2(password, salt)


def is_legacy_sha256_hash(password_hash: str) -> bool:
    """Return True when a stored password uses the legacy unsalted SHA-256 format."""
    return bool(password_hash) and "$" not in password_hash and len(password_hash) == 64


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against PBKDF2 hashes and legacy SHA-256 hashes."""
    if not password_hash:
        return False

    if is_legacy_sha256_hash(password_hash):
        legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(legacy_hash, password_hash)

    try:
        scheme, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
        if scheme != PBKDF2_SCHEME:
            return False

        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_hash = _hash_password_pbkdf2(password, salt, int(iterations))
        return hmac.compare_digest(expected_hash, password_hash)
    except Exception:
        return False

def check_session() -> Optional[Dict[str, Any]]:
    """
    Check if a user is logged in and return their info
    
    Returns:
        Dict with user info if authenticated, None otherwise
    """
    if not st.session_state.get("authenticated", False):
        return None

    user_info = st.session_state.get("user_info", {})
    expiration = user_info.get("exp")
    if expiration:
        try:
            expires_at = datetime.fromisoformat(expiration)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) >= expires_at:
                for key in ["authenticated", "username", "user_id", "role", "user_info"]:
                    st.session_state.pop(key, None)
                return None
        except ValueError:
            pass
    
    # Return user info
    return {
        "id": st.session_state.get("user_id") or user_info.get("user_id"),
        "username": st.session_state.get("username") or user_info.get("username"),
        "role": st.session_state.get("role") or user_info.get("role")
    }
