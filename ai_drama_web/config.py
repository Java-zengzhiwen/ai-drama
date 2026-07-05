from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_root: Path = Path("runtime-data")
    skills_root: Path = Path("skills")
    runtime_provider: str = "mock"
    runtime_model: str = ""
    model_config = SettingsConfigDict(env_prefix="AI_DRAMA_", extra="ignore")
