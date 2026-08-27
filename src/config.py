import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def _get_secret(name: str, default: str | None = None) -> str | None:
    """Look up a setting from, in order: environment variables (local .env
    via python-dotenv), then Streamlit Cloud's secrets store. The streamlit
    import is done lazily so main.py (CLI, no Streamlit) never needs it.
    """
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        return st.secrets.get(name, default)
    except Exception:
        return default


DEFAULT_MODEL = _get_secret("GROQ_MODEL", "openai/gpt-oss-20b")


@lru_cache(maxsize=1)
def get_llm(model: str | None = None, temperature: float = 0) -> ChatGroq:
    """Build (and cache) the Groq chat model. Lazy - called from nodes.py,
    not at import time - so importing the graph doesn't require an API key.
    """
    api_key = _get_secret("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY not found. Set it in a local .env file, or in "
            "Streamlit Cloud under App settings -> Secrets."
        )
    return ChatGroq(
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        groq_api_key=api_key,
    )
