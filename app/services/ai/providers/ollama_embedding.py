import logging

import httpx

from app.config import get_settings
from app.services.ai.exceptions import EmbeddingRateLimitError, EmbeddingServiceError
from app.services.ai.interfaces import EmbeddingService

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaEmbeddingService(EmbeddingService):
    def __init__(self) -> None:
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.embedding_model
        self._timeout = 60.0

    @staticmethod
    def _normalize_dimensions(vector: list[float], target_dimensions: int) -> list[float]:
        if len(vector) == target_dimensions:
            return vector
        if len(vector) > target_dimensions:
            logger.warning(
                "Embedding dimensions (%s) > target (%s); truncating",
                len(vector),
                target_dimensions,
            )
            return vector[:target_dimensions]

        logger.warning(
            "Embedding dimensions (%s) < target (%s); padding with zeros",
            len(vector),
            target_dimensions,
        )
        return vector + [0.0] * (target_dimensions - len(vector))

    @staticmethod
    def _extract_embeddings(payload: dict) -> list[list[float]]:
        if isinstance(payload.get("embeddings"), list):
            embeddings = payload["embeddings"]
            if embeddings and isinstance(embeddings[0], list):
                return embeddings

        if isinstance(payload.get("embedding"), list):
            return [payload["embedding"]]

        raise EmbeddingServiceError("Invalid embedding response format from Ollama")

    async def _request_embeddings(self, input_value: str | list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
            payload = {"model": self._model, "input": input_value}
            response = await client.post("/api/embed", json=payload)

            # Backward compatibility for old Ollama versions.
            if response.status_code == 404:
                if isinstance(input_value, list):
                    logger.warning(
                        "Ollama does not support batch /api/embed; falling back to sequential /api/embeddings"
                    )
                    results: list[list[float]] = []
                    for text in input_value:
                        r = await client.post(
                            "/api/embeddings",
                            json={"model": self._model, "prompt": text},
                        )
                        if r.status_code >= 400:
                            raise EmbeddingServiceError(
                                f"Ollama embedding request failed ({r.status_code}): {r.text}"
                            )
                        results.extend(self._extract_embeddings(r.json()))
                    return results
                response = await client.post(
                    "/api/embeddings",
                    json={"model": self._model, "prompt": input_value},
                )

            if response.status_code == 429:
                raise EmbeddingRateLimitError("Ollama embedding endpoint is rate-limited")

            if response.status_code >= 400:
                detail = response.text
                raise EmbeddingServiceError(
                    f"Ollama embedding request failed ({response.status_code}): {detail}"
                )

            return self._extract_embeddings(response.json())

    async def embed_text(self, text: str) -> list[float]:
        cleaned = text.replace("\n", " ")
        embeddings = await self._request_embeddings(cleaned)
        return self._normalize_dimensions(embeddings[0], settings.embedding_dimensions)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        cleaned = [t.replace("\n", " ") for t in texts]
        embeddings = await self._request_embeddings(cleaned)
        return [
            self._normalize_dimensions(vec, settings.embedding_dimensions) for vec in embeddings
        ]
