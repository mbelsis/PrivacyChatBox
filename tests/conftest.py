import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker


class SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def _noop(*args, **kwargs):
    return None


if "streamlit" not in sys.modules:
    streamlit_stub = types.ModuleType("streamlit")
    streamlit_stub.session_state = SessionState()
    streamlit_stub.error = _noop
    streamlit_stub.warning = _noop
    streamlit_stub.success = _noop
    streamlit_stub.info = _noop
    streamlit_stub.write = _noop
    streamlit_stub.markdown = _noop
    streamlit_stub.caption = _noop
    streamlit_stub.sidebar = types.SimpleNamespace(warning=_noop)
    sys.modules["streamlit"] = streamlit_stub

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = _noop
    dotenv_stub.dotenv_values = lambda *args, **kwargs: {}
    sys.modules["dotenv"] = dotenv_stub

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")
    openai_stub.OpenAI = object
    sys.modules["openai"] = openai_stub

if "anthropic" not in sys.modules:
    anthropic_stub = types.ModuleType("anthropic")
    anthropic_stub.Anthropic = object
    sys.modules["anthropic"] = anthropic_stub

if "google" not in sys.modules:
    google_stub = types.ModuleType("google")
    sys.modules["google"] = google_stub

if "google.generativeai" not in sys.modules:
    google_genai_stub = types.ModuleType("google.generativeai")
    google_genai_stub.GenerativeModel = object
    google_genai_stub.configure = _noop
    sys.modules["google.generativeai"] = google_genai_stub

if "msal" not in sys.modules:
    try:
        import msal  # noqa: F401
    except ImportError:
        msal_stub = types.ModuleType("msal")
        msal_stub.ConfidentialClientApplication = object
        sys.modules["msal"] = msal_stub

if "jose" not in sys.modules:
    try:
        import jose  # noqa: F401
    except ImportError:
        jose_stub = types.ModuleType("jose")
        jose_stub.jwt = types.SimpleNamespace()
        sys.modules["jose"] = jose_stub

if "reportlab" not in sys.modules:
    reportlab = types.ModuleType("reportlab")
    reportlab_lib = types.ModuleType("reportlab.lib")
    reportlab_pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    reportlab_pagesizes.letter = ("letter",)
    reportlab_colors = types.ModuleType("reportlab.lib.colors")
    reportlab_colors.blue = "blue"
    reportlab_colors.black = "black"
    reportlab_colors.gray = "gray"
    reportlab_colors.lightgrey = "lightgrey"
    reportlab_styles = types.ModuleType("reportlab.lib.styles")
    reportlab_styles.getSampleStyleSheet = lambda: {
        "Title": object(),
        "Heading2": object(),
        "Normal": object(),
    }
    reportlab_styles.ParagraphStyle = lambda *args, **kwargs: object()
    reportlab_platypus = types.ModuleType("reportlab.platypus")
    reportlab_platypus.SimpleDocTemplate = object
    reportlab_platypus.Paragraph = lambda *args, **kwargs: None
    reportlab_platypus.Spacer = lambda *args, **kwargs: None
    reportlab_platypus.Table = lambda *args, **kwargs: types.SimpleNamespace(setStyle=lambda *a, **k: None)
    reportlab_platypus.TableStyle = lambda *args, **kwargs: None

    sys.modules["reportlab"] = reportlab
    sys.modules["reportlab.lib"] = reportlab_lib
    sys.modules["reportlab.lib.pagesizes"] = reportlab_pagesizes
    sys.modules["reportlab.lib.colors"] = reportlab_colors
    sys.modules["reportlab.lib.styles"] = reportlab_styles
    sys.modules["reportlab.platypus"] = reportlab_platypus


import database
from database import Base


@pytest.fixture(autouse=True)
def reset_streamlit_state():
    import streamlit as st

    st.session_state.clear()
    yield
    st.session_state.clear()


@pytest.fixture
def sqlite_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    old_engine = database.engine
    old_session_local = database.SessionLocal

    database.engine = engine
    database.SessionLocal = session_local
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)
    engine.dispose()
    database.engine = old_engine
    database.SessionLocal = old_session_local
