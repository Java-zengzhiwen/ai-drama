from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_root: Path = Path("runtime-data")
    skills_root: Path = Path("skills")
    runtime_provider: str = "mock"
    runtime_model: str = ""
    agnes_image_endpoint: str = "https://apihub.agnes-ai.com/v1/images/generations"
    agnes_image_model: str = "agnes-image-2.1-flash"
    agnes_video_endpoint: str = "https://apihub.agnes-ai.com/v1/videos"
    agnes_video_status_endpoint: str = "https://apihub.agnes-ai.com/agnesapi"
    agnes_video_model: str = "agnes-video-v2.0"
    agnes_timeout_seconds: float = 60.0
    agnes_video_rpm: int = 1
    agnes_poll_interval_seconds: float = 5.0
    m6_supplier_execution_enabled: bool = False
    model_tests_enabled: bool = False
    public_base_url: str = ""
    trusted_management_proxy_cidrs: str = ""
    model_config = SettingsConfigDict(env_prefix="AI_DRAMA_", extra="ignore")
