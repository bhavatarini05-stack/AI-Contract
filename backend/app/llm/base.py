from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    """Interface every (free/local) LLM backend implements."""

    name: str = "base"
    model: str = ""

    @abstractmethod
    def chat(self, prompt: str, system: str | None = None, json_schema: dict | None = None) -> str:
        """Return the raw completion. If json_schema is given, the output must be JSON."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""

    @abstractmethod
    def health(self) -> dict:
        """Return {"ok": bool, ...details}."""

    def structured(self, prompt: str, schema: type[T], system: str | None = None) -> T:
        """Ask for JSON matching `schema`, validate it, retry once on failure."""
        json_schema = schema.model_json_schema()
        last_err: Exception | None = None
        for attempt in range(2):
            p = prompt
            if attempt and last_err:
                p += (
                    f"\n\nYour previous answer was invalid ({last_err}). "
                    "Reply ONLY with JSON matching the schema."
                )
            raw = self.chat(p, system=system, json_schema=json_schema)
            try:
                return schema.model_validate(json.loads(_strip_fences(raw)))
            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
                log.warning("LLM structured output invalid (attempt %s): %s", attempt + 1, e)
        raise LLMError(f"LLM failed to produce valid {schema.__name__}: {last_err}")


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        s = s.rsplit("```", 1)[0]
    return s.strip()
