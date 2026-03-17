from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    chat_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    class Config:
        env_file = ".env"

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
