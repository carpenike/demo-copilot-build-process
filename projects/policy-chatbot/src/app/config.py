"""Application configuration loaded from environment variables.

All secrets are injected by Azure Key Vault via ACA managed identity —
no credentials are stored in code or config files.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "POLICYCHAT_"}

    # --- Application ---
    app_name: str = "policy-chatbot"
    debug: bool = False

    # --- Database (Azure Database for PostgreSQL Flexible Server) ---
    database_url: str = Field(
        description="asyncpg connection string from Azure Key Vault",
    )

    # --- Redis (Azure Cache for Redis) ---
    redis_url: str = Field(
        description="Redis connection string from Azure Key Vault",
    )

    # --- Microsoft Entra ID (OIDC / MSAL) ---
    entra_tenant_id: str = Field(description="Entra ID tenant ID")
    entra_client_id: str = Field(description="Entra ID application client ID")
    entra_client_secret: str = Field(description="Entra ID client secret from Key Vault")

    # --- Azure OpenAI Service ---
    azure_openai_endpoint: str = Field(description="Azure OpenAI Service endpoint URL")
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_chat_deployment: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_embedding_dimensions: int = 1536

    # --- Azure AI Search ---
    azure_search_endpoint: str = Field(description="Azure AI Search endpoint URL")
    azure_search_index_name: str = "policy-chunks-v1"

    # --- Azure Blob Storage ---
    blob_account_url: str = Field(description="Azure Blob Storage account URL")
    blob_container_name: str = "policy-documents"

    # --- ServiceNow ---
    servicenow_instance_url: str = Field(description="ServiceNow instance URL")
    servicenow_api_user: str = Field(description="ServiceNow integration user from Key Vault")
    servicenow_api_password: str = Field(
        description="ServiceNow integration password from Key Vault",
    )

    # --- Microsoft Graph API ---
    graph_api_base_url: str = "https://graph.microsoft.com/v1.0"

    # --- RAG Configuration ---
    rag_top_k: int = 5
    rag_confidence_threshold: float = 0.6
    rag_max_conversation_history: int = 10

    # --- Session / Data Retention ---
    session_cache_ttl_seconds: int = 86400  # 24 hours for user profile cache
    conversation_ttl_days: int = 90

    # --- CORS ---
    cors_allowed_origins: list[str] = Field(
        default_factory=list,
        description="Explicit CORS origin allowlist — never use wildcard",
    )

    @property
    def entra_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}"

    @property
    def entra_jwks_url(self) -> str:
        return f"{self.entra_authority}/discovery/v2.0/keys"

    @property
    def entra_issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"


def get_settings() -> Settings:
    return Settings()
