from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMError, LLMProvider


@lru_cache
def get_provider() -> LLMProvider:
    """Return the configured free LLM backend (Ollama by default, mock for tests)."""
    s = get_settings()
    if s.llm_provider == "mock":
        from app.llm.mock_provider import MockProvider

        return MockProvider()
    if s.llm_provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            s.ollama_host, s.ollama_model, s.ollama_embed_model, s.llm_timeout_seconds
        )
    raise ValueError(f"Unknown LLM_PROVIDER={s.llm_provider!r} (supported: ollama, mock)")


__all__ = ["LLMError", "LLMProvider", "get_provider"]
