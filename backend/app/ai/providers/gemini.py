import time

import httpx

from app.ai.providers.base import LLMProvider, parse_json_text
from app.core.config import get_settings
from app.core.exceptions import LLMError


class GeminiProvider(LLMProvider):
    name = "gemini"

    def complete_json(self, system: str, user: str) -> dict:
        s = get_settings()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }
        headers = {"x-goog-api-key": s.gemini_api_key, "Content-Type": "application/json"}
        for attempt in range(2):
            try:
                r = httpx.post(url, json=body, headers=headers, timeout=s.llm_timeout_seconds)
            except httpx.HTTPError:
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise LLMError("Could not reach the Gemini API.")
            if r.status_code in (429, 500, 502, 503) and attempt == 0:
                time.sleep(2)
                continue
            if r.status_code != 200:
                raise LLMError(f"Gemini request failed (HTTP {r.status_code}). Check the API key and model name.")
            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                return parse_json_text("".join(p.get("text", "") for p in parts))
            except (KeyError, IndexError, ValueError):
                raise LLMError("Gemini returned an empty or blocked response.")
        raise LLMError("Gemini request failed.")
