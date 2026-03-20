"""Application configuration via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is read from environment variables prefixed POLICY_CHATBOT_."""

    model_config = SettingsConfigDict(
        env_prefix="POLICY_CHATBOT_",
        case_sensitive=False,
    )

    # --- FastAPI ---
    app_name: str = "policy-chatbot"
    debug: bool = False
    allowed_origins: str = "https://intranet.acme.com"

    # --- Database (Azure Database for PostgreSQL) ---
    database_url: str = "postgresql+asyncpg://localhost:5432/policychatbot"

    # --- Redis (Azure Cache for Redis) ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Azure Blob Storage ---
    blob_account_url: str = "https://stpolicychatbot.blob.core.windows.net"
    blob_container_name: str = "policy-docs"

    # --- Azure AI Search ---
    search_endpoint: str = "https://srch-policy-chatbot.search.windows.net"
    search_index_name: str = "policy-chunks"

    # --- Azure OpenAI ---
    openai_endpoint: str = "https://oai-policy-chatbot.openai.azure.com"
    openai_deployment: str = "gpt-4o"
    openai_embedding_deployment: str = "text-embedding-ada-002"
    openai_api_version: str = "2024-12-01-preview"

    # --- Microsoft Entra ID (auth) ---
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_authority: str = ""

    # --- Microsoft Graph ---
    graph_base_url: str = "https://graph.microsoft.com/v1.0"

    # --- ServiceNow ---
    servicenow_base_url: str = ""

    # --- Azure Monitor ---
    applicationinsights_connection_string: str = ""

    # --- Session ---
    session_ttl_seconds: int = 1800  # 30 minutes
