from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.services.ai.exceptions import EmbeddingRateLimitError, EmbeddingServiceError
from app.services.ai.factory import get_embedding_service


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((EmbeddingRateLimitError, EmbeddingServiceError)),
)
async def embed_text(text: str) -> list[float]:
    """Generate an embedding vector for the given text."""
    provider = get_embedding_service()
    return await provider.embed_text(text)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((EmbeddingRateLimitError, EmbeddingServiceError)),
)
async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for a batch of texts."""
    provider = get_embedding_service()
    return await provider.embed_batch(texts)
