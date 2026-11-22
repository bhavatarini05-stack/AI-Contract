from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"), extra="ignore"
    )

    llm_provider: str = "ollama"  # ollama | mock
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_embed_model: str = "nomic-embed-text"
    llm_timeout_seconds: float = 300

    tesseract_cmd: str = ""
    ocr_languages: str = "eng"

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'contracts.db').as_posix()}"
    storage_dir: Path = BACKEND_DIR.parent / "storage"

    # ---- Auth ----
    secret_key: str = ""  # JWT signing key; auto-generated into backend/.secret_key if empty
    session_hours: int = 12
    allow_registration: bool = True  # first registered account always becomes admin

    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # ---- Optional integrations (free sandbox / test modes only; off by default) ----
    fernet_key: str = ""
    enable_gdrive: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""

    enable_docusign: bool = False
    docusign_integration_key: str = ""
    docusign_secret_key: str = ""
    docusign_auth_server: str = "https://account-d.docusign.com"  # developer sandbox

    enable_dropbox_sign: bool = False
    dropbox_sign_api_key: str = ""
    dropbox_sign_test_mode: bool = True  # free, non-binding test requests

    enable_adobe_sign: bool = False
    adobe_sign_client_id: str = ""
    adobe_sign_client_secret: str = ""
    adobe_sign_shard: str = "na1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
