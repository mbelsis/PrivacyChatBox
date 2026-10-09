import sys
import types
import warnings

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


try:
    import streamlit  # noqa: F401
except ImportError:
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

try:
    import dotenv  # noqa: F401
except ImportError:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = _noop
    dotenv_stub.dotenv_values = lambda *args, **kwargs: {}
    sys.modules["dotenv"] = dotenv_stub

try:
    import openai  # noqa: F401
except ImportError:
    openai_stub = types.ModuleType("openai")
    openai_stub.OpenAI = object
    sys.modules["openai"] = openai_stub

try:
    import anthropic  # noqa: F401
except ImportError:
    anthropic_stub = types.ModuleType("anthropic")
    anthropic_stub.Anthropic = object
    sys.modules["anthropic"] = anthropic_stub

try:
    from google import genai  # noqa: F401
    from google.genai import types as _genai_types  # noqa: F401
except ImportError:
    google_pkg = sys.modules.setdefault("google", types.ModuleType("google"))
    google_genai_stub = types.ModuleType("google.genai")
    google_genai_stub.Client = object
    google_genai_types_stub = types.ModuleType("google.genai.types")
    google_genai_types_stub.Content = lambda **kwargs: types.SimpleNamespace(**kwargs)
    google_genai_types_stub.Part = types.SimpleNamespace(from_text=lambda text: types.SimpleNamespace(text=text))
    google_genai_types_stub.GenerateContentConfig = lambda **kwargs: types.SimpleNamespace(**kwargs)
    google_genai_stub.types = google_genai_types_stub
    google_pkg.genai = google_genai_stub
    sys.modules["google.genai"] = google_genai_stub
    sys.modules["google.genai.types"] = google_genai_types_stub

if "msal" not in sys.modules:
    try:
        import msal  # noqa: F401
    except ImportError:
        msal_stub = types.ModuleType("msal")
        msal_stub.ConfidentialClientApplication = object
        sys.modules["msal"] = msal_stub

try:
    import reportlab  # noqa: F401
except ImportError:
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


# Real Streamlit warns when session_state is used outside ``streamlit run``; that is
# expected for the pure-logic tests.
warnings.filterwarnings("ignore", message=".*Session state does not function.*")

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
