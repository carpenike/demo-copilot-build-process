"""Application configuration loaded from environment variables.

All secrets are injected by Azure Key Vault via the AKS CSI secrets driver —
no credentials are stored in code or config files.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "EXPENSE_"}

    # --- Application ---
    app_name: str = "expense-portal"
    debug: bool = False
    base_url: str = "https://expenses.acme.com"

    # --- Database (Azure Database for PostgreSQL) ---
    database_url: str = Field(
        description="asyncpg connection string from Azure Key Vault",
    )

    # --- Redis (Azure Cache for Redis) ---
    redis_url: str = Field(
        description="Redis connection string from Azure Key Vault",
    )

    # --- Microsoft Entra ID (OIDC) ---
    entra_tenant_id: str = Field(description="Entra ID tenant ID")
    entra_client_id: str = Field(description="Entra ID application client ID")
    entra_client_secret: str = Field(description="Entra ID client secret from Key Vault")

    # --- Azure Blob Storage ---
    blob_account_url: str = Field(description="Azure Blob Storage account URL")
    blob_container_name: str = "receipts"

    # --- Azure AI Document Intelligence ---
    docai_endpoint: str = Field(description="Document Intelligence endpoint URL")
    docai_key: str = Field(description="Document Intelligence API key from Key Vault")

    # --- SMTP ---
    smtp_host: str = "smtp.acme.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = Field(default="", description="SMTP password from Key Vault")
    smtp_from_address: str = "expenses@acme.com"

    # --- Session ---
    session_secret_key: str = Field(description="Session signing key from Key Vault")
    session_max_age_seconds: int = 86400  # 24 hours

    # --- OCR ---
    ocr_confidence_threshold: float = 0.85

    # --- Policy defaults ---
    finance_review_threshold: float = 500.00
    auto_escalation_business_days: int = 5
    reminder_business_days: int = 3

    @property
    def entra_authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.entra_tenant_id}"

    @property
    def entra_openid_config_url(self) -> str:
        return f"{self.entra_authority}/v2.0/.well-known/openid-configuration"


def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
