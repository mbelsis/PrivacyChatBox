from pathlib import Path
import tempfile

from database import session_scope
from models import Conversation, Message, User
import pdf_export


def test_export_conversation_to_pdf_escapes_markup(monkeypatch):
    captured_paragraphs = []
    temp_root = Path.cwd() / "tests_tmp"
    temp_root.mkdir(exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(dir=temp_root))

    class FakeDoc:
        def __init__(self, path, **kwargs):
            self.path = path

        def build(self, elements):
            self.built = True

    def fake_paragraph(text, style):
        captured_paragraphs.append(text)
        return ("paragraph", text)

    monkeypatch.setattr(
        pdf_export,
        "get_conversation",
        lambda *args, **kwargs: {
            "id": 1,
            "user_id": 7,
            "title": "Conversation <Title> & Notes",
            "created_at": __import__("datetime").datetime(2026, 1, 1, 12, 0, 0),
            "updated_at": __import__("datetime").datetime(2026, 1, 1, 12, 5, 0),
            "messages": [
                {
                    "role": "user",
                    "content": "if a < b and c > d: print('&')",
                    "files": [{"original_name": "code<sample>.py", "mime_type": "text/plain&utf8"}],
                },
                {
                    "role": "assistant",
                    "content": "Use <tag> carefully & escape content.",
                    "files": [],
                },
            ],
        },
    )
    monkeypatch.setattr(pdf_export, "get_user", lambda user_id: {"id": user_id, "username": "user<&>"})
    monkeypatch.setattr(pdf_export, "SimpleDocTemplate", FakeDoc)
    monkeypatch.setattr(pdf_export, "Paragraph", fake_paragraph)
    monkeypatch.setattr(pdf_export.tempfile, "gettempdir", lambda: str(temp_dir))

    pdf_path = pdf_export.export_conversation_to_pdf(1, requesting_user_id=7)

    assert str(pdf_path).endswith(".pdf")
    assert any("Conversation: Conversation &lt;Title&gt; &amp; Notes" in text for text in captured_paragraphs)
    assert any("if a &lt; b and c &gt; d: print('&amp;')" in text for text in captured_paragraphs)
    assert any("Use &lt;tag&gt; carefully &amp; escape content." in text for text in captured_paragraphs)
    assert any("code&lt;sample&gt;.py" in text for text in captured_paragraphs)


def test_get_conversation_respects_requesting_user_scope(sqlite_db):
    with session_scope() as session:
        owner = User(username="owner", password="hash", role="user")
        other = User(username="other", password="hash", role="user")
        session.add_all([owner, other])
        session.flush()

        conversation = Conversation(user_id=owner.id, title="Scoped Export")
        session.add(conversation)
        session.flush()

        session.add(Message(conversation_id=conversation.id, role="user", content="top secret"))
        conversation_id = conversation.id
        owner_id = owner.id
        other_id = other.id

    assert pdf_export.get_conversation(conversation_id, requesting_user_id=other_id) is None

    conversation = pdf_export.get_conversation(
        conversation_id,
        requesting_user_id=other_id,
        allow_admin_access=True,
    )

    assert conversation is not None
    assert conversation["user_id"] == owner_id
    assert conversation["messages"][0]["content"] == "top secret"
