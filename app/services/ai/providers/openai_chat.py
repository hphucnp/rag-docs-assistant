import httpx

from app.config import get_settings
from app.services.ai.exceptions import (
    ChatConfigurationError,
    ChatRateLimitError,
    ChatServiceError,
)
from app.services.ai.interfaces import ChatService

settings = get_settings()


class OpenAIChatService(ChatService):
    def __init__(self) -> None:
        self._base_url = settings.openai_base_url.rstrip("/")
        self._api_key = settings.openai_api_key
        self._timeout = 60.0

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
    ) -> str:
        if not self._api_key:
            raise ChatConfigurationError("OPENAI_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )

        if response.status_code == 429:
            raise ChatRateLimitError("OpenAI chat endpoint is rate-limited")

        if response.status_code >= 400:
            raise ChatServiceError(
                f"OpenAI chat request failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ChatServiceError("OpenAI response has no choices")

        content = choices[0].get("message", {}).get("content")
        return content or ""
