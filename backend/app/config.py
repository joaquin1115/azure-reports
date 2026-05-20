from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "AzureReport API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/azurereport"

    # Azure Entra ID (API auth)
    azure_tenant_id: str = "aa3caa64-02b4-4eba-b442-333bedb5121b"
    azure_client_id: str = "d323155c-9db3-4db8-814b-1a72ad9ee632"  # App registration client ID

    use_managed_identity: bool = True
    managed_identity_client_id: str = ""

    # Azure credentials for ARM/Advisor calls (Managed Identity only)
    managed_identity_client_id: str = ""

    # Azure Blob Storage
    azure_storage_connection_string: str = "YOUR_STORAGE_CONNECTION_STRING"
    azure_storage_container: str = "reportes"

    # JWT / JWKS
    jwks_uri: str = ""  # Auto-built from tenant_id

    # CORS
    allowed_origins: list[str] = ["https://proud-pond-071d4800f.7.azurestaticapps.net"]

    def model_post_init(self, __context):
        if not self.jwks_uri:
            object.__setattr__(
                self,
                "jwks_uri",
                f"https://login.microsoftonline.com/{self.azure_tenant_id}/discovery/v2.0/keys",
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
