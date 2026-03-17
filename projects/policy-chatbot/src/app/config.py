"""Application configuration via environment variables.

Uses pydantic-settings to load configuration from environment variables with
the POLICY_CHATBOT_ prefix. All Azure service connection details are loaded
here — no secrets are hardcoded.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="POLICY_CHATBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "policy-chatbot"
    debug: bool = False
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(
        default=["https://intranet.acme.com"],
        description="Explicit CORS origins — never use wildcard",
    )

    # --- Database (Azure Database for PostgreSQL) ---
    database_url: str = Field(
        description="PostgreSQL async connection string (postgresql+asyncpg://...)"
    )

    # --- Redis (Azure Cache for Redis) ---
    redis_url: str = Field(description="Redis connection string (rediss://...)")
    redis_session_ttl_seconds: int = Field(
        default=1800, description="Conversation context TTL in Redis (30 min)"
    )
    redis_profile_ttl_seconds: int = Field(
        default=3600, description="Employee profile cache TTL in Redis (1 hour)"
    )

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = Field(description="Azure OpenAI endpoint URL")
    azure_openai_api_version: str = Field(default="2024-12-01-preview")
    azure_openai_chat_deployment: str = Field(
        default="gpt-4o", description="Deployment name for answer generation"
    )
    azure_openai_classifier_deployment: str = Field(
        default="gpt-4o-mini", description="Deployment name for intent classification"
    )
    azure_openai_embedding_deployment: str = Field(
        default="text-embedding-3-large", description="Deployment name for embeddings"
    )
    azure_openai_embedding_dimensions: int = Field(
        default=3072, description="Embedding vector dimensions"
    )

    # --- Azure AI Search ---
    azure_search_endpoint: str = Field(description="Azure AI Search endpoint URL")
    azure_search_index_name: str = Field(default="policy-documents")

    # --- Azure Blob Storage ---
    azure_storage_account_url: str = Field(description="Azure Blob Storage account URL")
    azure_storage_container_raw: str = Field(default="policy-documents")
    azure_storage_container_processed: str = Field(default="processed-documents")

    # --- Azure Monitor ---
    applicationinsights_connection_string: str = Field(
        default="", description="Application Insights connection string"
    )

    # --- Entra ID / Auth ---
    azure_tenant_id: str = Field(description="Microsoft Entra ID tenant ID")
    azure_client_id: str = Field(description="App registration client ID")
    azure_client_secret: str = Field(
        default="", description="App registration client secret (use managed identity in prod)"
    )

    # --- Bot Framework ---
    bot_app_id: str = Field(default="", description="Bot Framework app ID")
    bot_app_password: str = Field(default="", description="Bot Framework app password")

    # --- RAG Pipeline ---
    rag_confidence_threshold: float = Field(
        default=0.6, description="Minimum confidence for an answer to be returned"
    )
    rag_max_escalation_attempts: int = Field(
        default=2, description="Auto-escalate after this many low-confidence answers"
    )
    rag_top_k: int = Field(default=5, description="Number of document chunks to retrieve")

    # --- Celery ---
    celery_broker_url: str = Field(default="", description="Celery broker URL (defaults to redis)")

    @property
    def effective_celery_broker_url(self) -> str:
        """Return the Celery broker URL, falling back to the Redis URL."""
        return self.celery_broker_url or self.redis_url
