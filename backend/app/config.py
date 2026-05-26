from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "AzureReport API"
    debug: bool = False

    # Database
    database_url: str

    # Azure Entra ID (API auth)
    azure_tenant_id: str
    azure_client_id: str  # App registration client ID

    use_managed_identity: bool = True
    managed_identity_client_id: str = ""

    # Azure Blob Storage
    azure_storage_connection_string: str
    azure_storage_container: str = "reportes"

    # JWT / JWKS
    jwks_uri: str = ""  # Auto-built from tenant_id

    # Azure Translator
    azure_translator_key: str
    azure_translator_endpoint: str
    azure_translator_region: str

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
