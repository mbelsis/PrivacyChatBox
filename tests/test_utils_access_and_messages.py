from database import session_scope
from models import Conversation, User
from utils import add_message_to_conversation, create_new_conversation, delete_conversation, get_conversation


def create_user_record(username, role="user"):
    with session_scope() as session:
        user = User(username=username, password="hash", role=role)
        session.add(user)
        session.flush()
        return user.id


def test_get_conversation_enforces_owner_scope(sqlite_db):
    owner_id = create_user_record("owner")
    other_id = create_user_record("other")
    conversation_id = create_new_conversation(owner_id)
    add_message_to_conversation(conversation_id, "user", "hello from owner")

    assert get_conversation(conversation_id, requesting_user_id=other_id) is None

    conversation = get_conversation(conversation_id, requesting_user_id=other_id, allow_admin_access=True)
    assert conversation is not None
    assert conversation["user_id"] == owner_id


def test_delete_conversation_enforces_owner_scope(sqlite_db):
    owner_id = create_user_record("delete-owner")
    other_id = create_user_record("delete-other")
    conversation_id = create_new_conversation(owner_id)

    assert delete_conversation(conversation_id, requesting_user_id=other_id) is False

    with session_scope() as session:
        assert session.query(Conversation).filter(Conversation.id == conversation_id).first() is not None

    assert delete_conversation(conversation_id, requesting_user_id=other_id, allow_admin_access=True) is True

    with session_scope() as session:
        assert session.query(Conversation).filter(Conversation.id == conversation_id).first() is None


def test_add_message_updates_new_conversation_title(sqlite_db):
    owner_id = create_user_record("title-owner")
    conversation_id = create_new_conversation(owner_id)
    content = "This is the first user message for title generation"

    message_id, error = add_message_to_conversation(conversation_id, "user", content)

    assert message_id > 0
    assert error is None

    with session_scope() as session:
        conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
        assert conversation.title == "This is the first user message..."
