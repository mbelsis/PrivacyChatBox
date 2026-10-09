"""End-to-end page tests driven through Streamlit's AppTest harness.

These exercise the real page scripts (login, chat, history, settings, admin,
analytics, model manager) against a throw-away SQLite database. They are skipped
when Streamlit is not installed, so the pure-logic suite still runs in minimal
environments.
"""

import os
import sys
import types
from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
pytest.importorskip("streamlit.testing.v1")
if not hasattr(streamlit, "chat_input"):  # the stub from conftest, not the real package
    pytest.skip("real streamlit package required", allow_module_level=True)

from streamlit.testing.v1 import AppTest  # noqa: E402

import database  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PAGE_TIMEOUT = 60


@pytest.fixture
def app_db(tmp_path, monkeypatch):
    """Point the application at a fresh SQLite database for the duration of a test."""
    db_url = f"sqlite:///{tmp_path / 'pages.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("ALLOW_SELF_REGISTRATION", "true")
    # auth.py evaluates the flag at import time, and another test may already have
    # imported it, so patch the module attribute as well.
    import auth
    monkeypatch.setattr(auth, "ALLOW_SELF_REGISTRATION", True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(database, "DATABASE_URL", db_url)
    monkeypatch.setattr(database, "engine", None)
    monkeypatch.setattr(database, "SessionLocal", None)
    monkeypatch.chdir(REPO)

    assert database.init_db() is True
    yield db_url
    if database.engine is not None:
        database.engine.dispose()


def _page(name):
    return AppTest.from_file(str(REPO / name), default_timeout=PAGE_TIMEOUT)


def _login(at, user_id, username, role):
    at.session_state["authenticated"] = True
    at.session_state["user_id"] = user_id
    at.session_state["username"] = username
    at.session_state["role"] = role
    at.session_state["must_change_password"] = False
    at.session_state["user_info"] = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": "2099-01-01T00:00:00",
    }
    return at


def _text(at):
    parts = []
    for collection in (at.markdown, at.title, at.header, at.subheader, at.info, at.warning, at.error, at.success):
        parts.extend(element.value for element in collection)
    return " ".join(parts)


def _assert_clean(at, expect=None):
    assert not at.exception, [e.value for e in at.exception]
    if expect:
        assert expect in _text(at)


def _seed_users():
    from auth import create_user
    from database import session_scope
    from models import User

    # The bootstrap admin is normally created by app.py (init_auth); page tests that do
    # not render app.py first need an admin account as well.
    assert create_user("admin", "adminpass123", role="admin")
    assert create_user("alice", "password123", role="user", allow_when_registration_disabled=True)
    with session_scope() as session:
        return {user.username: user.id for user in session.query(User).all()}


def test_landing_registration_and_login(app_db):
    at = _page("app.py").run()
    _assert_clean(at, "Welcome to PrivacyChatBoX")

    at.text_input("reg_username").input("newuser")
    at.text_input("reg_password").input("password123")
    at.text_input("reg_password_confirm").input("password123")
    at.button("register_button").click().run()
    _assert_clean(at, "Registration successful")

    at.text_input("login_username").input("newuser")
    at.text_input("login_password").input("password123")
    at.button("login_button").click().run()
    _assert_clean(at, "Welcome back, newuser")
    assert at.session_state["authenticated"] is True

    # The bootstrap admin is created with a temporary password and must change it.
    import auth
    from database import session_scope
    from models import User
    from utils_auth import hash_password

    with session_scope() as session:
        admin_row = session.query(User).filter(User.username == auth.DEFAULT_BOOTSTRAP_ADMIN_USERNAME).one()
        assert admin_row.must_change_password is True
        assert not auth.is_using_bootstrap_password(admin_row)  # never admin/admin
        admin_row.password = hash_password("temporary-pass-123")

    admin = _page("app.py").run()
    admin.text_input("login_username").input(auth.DEFAULT_BOOTSTRAP_ADMIN_USERNAME)
    admin.text_input("login_password").input("temporary-pass-123")
    admin.button("login_button").click().run()
    _assert_clean(admin, "Your password is temporary")


def test_history_page_handles_zero_conversations(app_db):
    ids = _seed_users()
    at = _login(_page("pages/history.py"), ids["alice"], "alice", "user").run()
    _assert_clean(at, "don't have any conversations")


def test_chat_review_flow_completes_without_looping(app_db):
    from database import session_scope
    from models import Message
    from utils import create_new_conversation, update_user_settings

    ids = _seed_users()
    alice = ids["alice"]
    update_user_settings(alice, {"auto_anonymize": False})
    conversation_id = create_new_conversation(alice)

    at = _login(_page("pages/chat.py"), alice, "alice", "user")
    at.session_state["current_conversation_id"] = conversation_id
    at.run()
    _assert_clean(at, "Conversation:")

    at.chat_input[0].set_value("call me at 555-123-4567 please").run()
    _assert_clean(at, "Sensitive information was detected")
    assert at.session_state.get("pending_chat_submission")

    at.button("anonymize_sensitive").click().run()
    # No API key configured: the pre-check error is shown and the flow terminates.
    _assert_clean(at, "OPENAI_API_KEY")
    assert not at.session_state.get("pending_chat_submission")

    with session_scope() as session:
        messages = [
            (m.role, m.content)
            for m in session.query(Message).filter(Message.conversation_id == conversation_id).all()
        ]
    user_contents = [content for role, content in messages if role == "user"]
    assert len(user_contents) == 1
    assert "555-123-4567" not in user_contents[0]
    # Configuration errors must not be persisted as assistant turns.
    assert not [role for role, _ in messages if role == "assistant"]


def test_admin_pages_render_and_delete_user_confirms(app_db):
    from database import session_scope
    from models import DetectionEvent, User
    from utils import create_new_conversation, add_message_to_conversation

    ids = _seed_users()
    conversation_id = create_new_conversation(ids["alice"])
    add_message_to_conversation(conversation_id, "user", "hello")
    with session_scope() as session:
        session.add(DetectionEvent(user_id=ids["alice"], action="scan", severity="medium",
                                   detected_patterns={"email": ["a@b.com"]}))

    at = _login(_page("pages/admin.py"), ids["admin"], "admin", "admin").run()
    _assert_clean(at, "User Management")
    # Privacy log rows are formatted inside the session and therefore visible.
    assert "Showing 1 most recent events" in _text(at)

    selector = [sb for sb in at.selectbox if sb.key == "delete_user"][0]
    selector.select([o for o in selector.options if o.startswith("alice")][0]).run()
    at.button[[b.label for b in at.button].index("Delete User")].click().run()
    _assert_clean(at, "Are you sure you want to delete user 'alice'")
    at.button("confirm_delete").click().run()
    _assert_clean(at)
    with session_scope() as session:
        assert session.query(User).filter(User.username == "alice").first() is None

    analytics = _login(_page("pages/analytics.py"), ids["admin"], "admin", "admin").run()
    _assert_clean(analytics, "Advanced Analytics Dashboard")

    history = _login(_page("pages/history.py"), ids["admin"], "admin", "admin").run()
    _assert_clean(history, "All User Conversations")

    models = _login(_page("pages/model_manager.py"), ids["admin"], "admin", "admin").run()
    _assert_clean(models, "Model Manager")


def test_regular_user_is_denied_admin_pages(app_db):
    ids = _seed_users()
    admin = _login(_page("pages/admin.py"), ids["alice"], "alice", "user").run()
    _assert_clean(admin, "permission")
    analytics = _login(_page("pages/analytics.py"), ids["alice"], "alice", "user").run()
    _assert_clean(analytics, "Access denied")


def test_expired_session_is_logged_out_gracefully(app_db):
    ids = _seed_users()
    at = _login(_page("pages/chat.py"), ids["alice"], "alice", "user")
    at.session_state["user_info"]["exp"] = "2000-01-01T00:00:00"
    at.run()
    _assert_clean(at, "session has expired")
    assert not at.session_state.get("authenticated")
