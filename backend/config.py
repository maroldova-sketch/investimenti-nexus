from pydantic_settings import BaseSettings
from functools import lru_cache
import pathlib

class Settings(BaseSettings):
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    database_url: str = "sqlite:///./nexus.db"
    nexus_admin_email: str = "admin@holding.local"
    nexus_admin_password: str = "changeme123"
    nexus_env: str = "development"
    nexus_data_dir: str = str(pathlib.Path.home() / "Projects" / "nexus-data")

    # Microsoft 365
    m365_tenant_id: str = ""
    m365_client_id: str = ""
    m365_client_secret: str = ""
    m365_refresh_token: str = ""
    m365_scopes: str = "User.Read Mail.Read Mail.Send Calendars.Read Contacts.Read Files.Read.All"

    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()
