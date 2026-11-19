"""Provider interface. Every provider returns a parsed JSON object, so the rest of the system
is provider-agnostic."""
import json
import re
from abc import ABC, abstractmethod

from app.core.exceptions import LLMError


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def complete_json(self, system: str, user: str) -> dict:
        """Send a prompt, return the model's JSON answer as a dict. Raises LLMError."""


def parse_json_text(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("The AI provider returned an unreadable response.")
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            raise LLMError("The AI provider returned an unreadable response.")
    if not isinstance(data, dict):
        raise LLMError("The AI provider returned an unexpected response shape.")
    return data
