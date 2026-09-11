"""Lazy provider construction; importing this module makes no network calls."""
from ..config import AISettings


def build_chat_model(settings: AISettings):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise RuntimeError('AI support is not installed; run: pip install -e ".[agent]"') from exc
    return ChatOpenAI(
        api_key=settings.api_key.get_secret_value(), base_url=str(settings.base_url), model=settings.model,
        temperature=0, timeout=settings.timeout_seconds, max_retries=0,
    )
