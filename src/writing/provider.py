from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request


class ModelProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


@dataclass(slots=True)
class ProviderConfig:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.4
    max_tokens: int = 1200


class OpenAICompatibleProvider:
    """Optional OpenAI-compatible client with no extra dependencies."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "OpenAICompatibleProvider":
        api_key = os.getenv("OPENAI_API_KEY", "")
        model = os.getenv("OPENAI_MODEL", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if not api_key or not model:
            raise RuntimeError(
                "Missing OPENAI_API_KEY or OPENAI_MODEL. This provider is optional; "
                "the default project workflow is to let the current agent session read prompt files and write section drafts directly."
            )
        return cls(ProviderConfig(api_key=api_key, model=model, base_url=base_url))

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": "You write concise Chinese academic prose and must obey evidence boundaries.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        body = json.dumps(payload).encode("utf-8")
        chat_url = self.config.base_url.rstrip("/") + "/chat/completions"
        req = request.Request(
            chat_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Model request failed: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Model request failed: {exc}") from exc

        try:
            return payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Model response format was not recognized.") from exc
