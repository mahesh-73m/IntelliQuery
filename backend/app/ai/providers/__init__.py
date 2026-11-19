from app.ai.providers.base import LLMProvider
from app.core.config import get_settings
from app.core.exceptions import AppError

PROVIDERS = ("gemini", "groq", "openai")


def configured_providers() -> dict[str, bool]:
    s = get_settings()
    return {"gemini": bool(s.gemini_api_key), "groq": bool(s.groq_api_key), "openai": bool(s.openai_api_key)}


def get_provider(name: str | None = None) -> LLMProvider:
    name = (name or get_settings().llm_provider).lower()
    if name not in PROVIDERS:
        raise AppError(f"Unknown AI provider '{name}'.", 400)
    if not configured_providers()[name]:
        raise AppError(f"The '{name}' provider has no API key configured. Set {name.upper()}_API_KEY in .env.", 400)
    if name == "gemini":
        from app.ai.providers.gemini import GeminiProvider
        return GeminiProvider()
    if name == "groq":
        from app.ai.providers.groq import GroqProvider
        return GroqProvider()
    from app.ai.providers.openai import OpenAIProvider
    return OpenAIProvider()
