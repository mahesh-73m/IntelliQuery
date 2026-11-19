"""Shared client for OpenAI-compatible chat-completions APIs (OpenAI itself and Groq)."""
import time

import httpx

from app.ai.providers.base import LLMProvider, parse_json_text
from app.core.config import get_settings
from app.core.exceptions import LLMError


class OpenAICompatibleProvider(LLMProvider):
    base_url: str
    label: str

    def _key_and_model(self) -> tuple[str, str]:
        raise NotImplementedError

    def complete_json(self, system: str, user: str) -> dict:
        key, model = self._key_and_model()
        body = {
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system + "\nRespond with a single JSON object only."},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        timeout = get_settings().llm_timeout_seconds
        for attempt in range(2):
            try:
                r = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=timeout)
            except httpx.HTTPError:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise LLMError(f"Could not reach the {self.label} API.")
            if r.status_code in (429, 500, 502, 503) and attempt == 0:
                time.sleep(2)
                continue
            if r.status_code != 200:
                raise LLMError(f"{self.label} request failed (HTTP {r.status_code}). Check the API key and model name.")
            try:
                return parse_json_text(r.json()["choices"][0]["message"]["content"])
            except (KeyError, IndexError, ValueError):
                raise LLMError(f"{self.label} returned an empty response.")
        raise LLMError(f"{self.label} request failed.")
