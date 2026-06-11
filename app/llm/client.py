from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app.config import Settings


@dataclass
class LLMClient:
    """Minimal OpenAI-compatible chat completions client."""

    api_key: str | None
    base_url: str
    model: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMClient":
        return cls(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url.rstrip("/"),
            model=settings.openai_model,
        )

    @property
    def available(self) -> bool:
        """Return whether a live LLM call can be attempted."""

        return bool(self.api_key and self.api_key.strip())

    @property
    def mode(self) -> str:
        """Return the public LLM mode label for API responses."""

        return "openai-compatible" if self.available else "fallback"

    def complete_json(self, system_prompt: str, user_payload: dict[str, Any]) -> Any:
        """Call an OpenAI-compatible chat completion and parse JSON response."""

        if not self.available:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        content = payload["choices"][0]["message"]["content"]
        return json.loads(content)

