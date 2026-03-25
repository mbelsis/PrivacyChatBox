from datetime import datetime, timedelta, timezone

import streamlit as st

import auth
from database import session_scope
from models import Settings, User
from utils_auth import check_session, verify_password


def test_create_user_respects_self_registration_flag(sqlite_db, monkeypatch):
    monkeypatch.setattr(auth, "ALLOW_SELF_REGISTRATION", False)

    assert auth.create_user("blocked-user", "password123", role="user") is False

    with session_scope() as session:
        assert session.query(User).filter(User.username == "blocked-user").first() is None


def test_create_user_allows_admin_override_when_registration_disabled(sqlite_db, monkeypatch):
    monkeypatch.setattr(auth, "ALLOW_SELF_REGISTRATION", False)

    assert auth.create_user(
        "created-by-admin",
        "password123",
        role="user",
        allow_when_registration_disabled=True,
    ) is True


def test_check_session_expires_and_clears_state():
    st.session_state.authenticated = True
    st.session_state.username = "expired-user"
    st.session_state.user_id = 77
    st.session_state.role = "user"
    st.session_state.user_info = {
        "user_id": 77,
        "username": "expired-user",
        "role": "user",
        "exp": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    }

    assert check_session() is None
    assert st.session_state.get("authenticated") is None
    assert st.session_state.get("user_info") is None
