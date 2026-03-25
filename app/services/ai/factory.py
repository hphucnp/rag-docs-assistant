from app.config import get_settings
from app.services.ai.interfaces import ChatService, EmbeddingService
from app.services.ai.providers.groq_chat import GroqChatService
from app.services.ai.providers.ollama_embedding import OllamaEmbeddingService

settings = get_settings()

_embedding_service: EmbeddingService | None = None
_chat_service: ChatService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        provider = settings.embedding_provider.lower()
        if provider == "ollama":
            _embedding_service = OllamaEmbeddingService()
        else:
            raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
    return _embedding_service


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        provider = settings.chat_provider.lower()
        if provider == "groq":
            _chat_service = GroqChatService()
        else:
            raise ValueError(f"Unsupported chat provider: {settings.chat_provider}")
    return _chat_service
