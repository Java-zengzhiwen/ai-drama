from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_root: Path = Path("runtime-data")
    skills_root: Path = Path("skills")
    runtime_provider: str = "mock"
    runtime_model: str = ""
    agnes_image_endpoint: str = "https://apihub.agnes-ai.com/v1/images/generations"
    agnes_image_model: str = "agnes-image-2.1-flash"
    agnes_timeout_seconds: float = 60.0
    model_config = SettingsConfigDict(env_prefix="AI_DRAMA_", extra="ignore")
