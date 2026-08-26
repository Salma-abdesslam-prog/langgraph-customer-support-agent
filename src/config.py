import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")


@lru_cache(maxsize=1)
def get_llm(model: str | None = None, temperature: float = 0) -> ChatGroq:
    """Build (and cache) the Groq chat model. Lazy - called from nodes.py,
    not at import time - so importing the graph doesn't require an API key.
    """
    return ChatGroq(
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        groq_api_key=os.environ["GROQ_API_KEY"],
    )
