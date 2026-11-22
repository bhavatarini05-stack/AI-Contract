import httpx

from app.llm.base import LLMError, LLMProvider


class OllamaProvider(LLMProvider):
    """Free, local LLM via Ollama (https://ollama.com). No API key, no cost."""

    name = "ollama"

    def __init__(self, host: str, model: str, embed_model: str, timeout: float = 300):
        self.host = host.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self.client = httpx.Client(timeout=timeout)

    def chat(self, prompt: str, system: str | None = None, json_schema: dict | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0, "num_ctx": 8192},
        }
        if json_schema is not None:
            body["format"] = json_schema  # Ollama structured outputs
        try:
            r = self.client.post(f"{self.host}/api/chat", json=body)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama request failed: {e}") from e
        return r.json()["message"]["content"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            r = self.client.post(
                f"{self.host}/api/embed", json={"model": self.embed_model, "input": texts}
            )
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Ollama embed failed: {e}") from e
        return r.json()["embeddings"]

    def health(self) -> dict:
        try:
            r = self.client.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
        except httpx.HTTPError as e:
            return {
                "ok": False,
                "provider": self.name,
                "model": self.model,
                "error": str(e),
                "hint": "Install Ollama from https://ollama.com and make sure it is running.",
            }
        has_model = any(m == self.model or m.split(":")[0] == self.model for m in models)
        return {
            "ok": has_model,
            "provider": self.name,
            "model": self.model,
            "installed_models": models,
            "hint": None if has_model else f"Run: ollama pull {self.model}",
        }
