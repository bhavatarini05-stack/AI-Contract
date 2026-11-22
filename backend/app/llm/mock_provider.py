import hashlib
import json

from app.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """Deterministic offline provider for tests and CI.

    Structured calls return "{}" (schema defaults), so the pipeline falls back to
    its rule-based logic. Override with `responses`: {prompt_substring: json_or_text}.
    """

    name = "mock"
    model = "mock"

    def __init__(self, responses: dict[str, str | dict] | None = None):
        self.responses = responses or {}
        self.calls: list[str] = []

    def chat(self, prompt: str, system: str | None = None, json_schema: dict | None = None) -> str:
        self.calls.append(prompt)
        for key, val in self.responses.items():
            if key in prompt:
                return json.dumps(val) if isinstance(val, dict) else val
        return "{}" if json_schema is not None else ""

    def embed(self, texts: list[str]) -> list[list[float]]:
        # Hashed bag-of-words: deterministic and crudely semantic.
        out = []
        for t in texts:
            vec = [0.0] * 128
            for w in t.lower().split():
                vec[int(hashlib.md5(w.encode()).hexdigest(), 16) % 128] += 1.0
            out.append(vec)
        return out

    def health(self) -> dict:
        return {"ok": True, "provider": self.name, "model": self.model}
