class ProviderError(Exception):
    """Base exception for all external AI provider errors."""


class EmbeddingServiceError(ProviderError):
    """Raised when the embedding provider returns an unexpected error."""


class EmbeddingRateLimitError(EmbeddingServiceError):
    """Raised when the embedding provider applies rate limiting."""


class ChatServiceError(ProviderError):
    """Raised when the chat provider returns an unexpected error."""


class ChatRateLimitError(ChatServiceError):
    """Raised when the chat provider applies rate limiting."""


class ChatConfigurationError(ChatServiceError):
    """Raised when required chat provider configuration is missing."""
