from app.ai.providers.openai_compat import OpenAICompatibleProvider
from app.core.config import get_settings


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"
    label = "Groq"
    base_url = "https://api.groq.com/openai/v1"

    def _key_and_model(self):
        s = get_settings()
        return s.groq_api_key, s.groq_model
