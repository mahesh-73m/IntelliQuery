from app.ai.providers.openai_compat import OpenAICompatibleProvider
from app.core.config import get_settings


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    label = "OpenAI"
    base_url = "https://api.openai.com/v1"

    def _key_and_model(self):
        s = get_settings()
        return s.openai_api_key, s.openai_model
