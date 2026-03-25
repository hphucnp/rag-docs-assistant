import httpx

from app.config import get_settings
from app.services.ai.exceptions import EmbeddingRateLimitError, EmbeddingServiceError
from app.services.ai.interfaces import EmbeddingService

settings = get_settings()


class CohereEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        self._base_url = settings.cohere_base_url.rstrip("/")
        self._api_key = settings.cohere_api_key
        self._model = settings.embedding_model
        self._timeout = 60.0

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise EmbeddingServiceError("COHERE_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        payload = {
            "model": self._model,
            "texts": texts,
            "input_type": "search_document",
            "embedding_types": ["float"],
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                headers=self._headers(),
                json=payload,
            )

        if response.status_code == 429:
            raise EmbeddingRateLimitError("Cohere embedding endpoint is rate-limited")

        if response.status_code >= 400:
            raise EmbeddingServiceError(
                f"Cohere embedding request failed ({response.status_code}): {response.text}"
            )

        data = response.json()
        float_vectors = data.get("embeddings", {}).get("float", [])
        if not float_vectors:
            raise EmbeddingServiceError("Cohere response has no float embeddings")
        return float_vectors

    async def embed_text(self, text: str) -> list[float]:
        cleaned = text.replace("\n", " ")
        embeddings = await self._request_embeddings([cleaned])
        return embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.replace("\n", " ") for t in texts]
        return await self._request_embeddings(cleaned)
