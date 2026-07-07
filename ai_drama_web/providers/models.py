from dataclasses import dataclass, field


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    size: str
    input_images: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VideoGenerationRequest:
    prompt: str
    duration_seconds: int
    input_images: list[str] = field(default_factory=list)
    negative_prompt: str = ""
    parameters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderJob:
    provider_job_id: str
    status: str
    raw: dict


@dataclass(frozen=True)
class ProviderResult:
    provider_job_id: str
    media_type: str
    url: str
    content: bytes | None
    raw: dict
