from app.config import get_settings
from app.services.ai.interfaces import ChatService, EmbeddingService
from app.services.ai.providers.cohere_embedding import CohereEmbeddingService
from app.services.ai.providers.groq_chat import GroqChatService
from app.services.ai.providers.ollama_embedding import OllamaEmbeddingService
from app.services.ai.providers.openai_chat import OpenAIChatService
from app.services.ai.providers.openai_embedding import OpenAIEmbeddingService

settings = get_settings()

_embedding_service: EmbeddingService | None = None
_chat_service: ChatService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        provider = settings.embedding_provider.lower()
        if provider == "ollama":
            _embedding_service = OllamaEmbeddingService()
        elif provider == "openai":
            _embedding_service = OpenAIEmbeddingService()
        elif provider == "cohere":
            _embedding_service = CohereEmbeddingService()
        else:
            raise ValueError(
                "Unsupported embedding provider: "
                f"{settings.embedding_provider}. Supported: ollama, openai, cohere"
            )
    return _embedding_service


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        provider = settings.chat_provider.lower()
        if provider == "groq":
            _chat_service = GroqChatService()
        elif provider == "openai":
            _chat_service = OpenAIChatService()
        else:
            raise ValueError(
                f"Unsupported chat provider: {settings.chat_provider}. Supported: groq, openai"
            )
    return _chat_service
