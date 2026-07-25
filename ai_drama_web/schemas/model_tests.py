from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelTestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=4000)
    reasoning_effort: str | None = Field(default=None, min_length=1, max_length=16)
    size: str | None = Field(default=None, min_length=1, max_length=24)
    quality: str | None = Field(default=None, min_length=1, max_length=16)
    ratio: str | None = Field(default=None, min_length=1, max_length=16)


class ModelTestFeatureStatus(BaseModel):
    enabled: bool


class ModelTestRead(BaseModel):
    test_run_id: str
    supplier_model_id: str
    capability: Literal["text", "image"]
    status: Literal[
        "queued", "submitting", "completed", "failed", "submission_outcome_unknown"
    ]
    created_at: str
    started_at: str = ""
    finished_at: str = ""
    output: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    media_type: str = ""
    byte_size: int = 0
    elapsed_ms: int = 0
    error_code: str = ""
    error_message: str = ""
    reasoning_effort: str = ""
    size: str = ""
    quality: str = ""
    ratio: str = ""
