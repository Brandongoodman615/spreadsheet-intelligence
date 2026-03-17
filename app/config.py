from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    openai_model: str = "gpt-4o"
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
