from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class VideoJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_revision_id: str
    shot_id: str
    idempotency_key: str
    overrides: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt_revision_id", "shot_id", "idempotency_key")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _not_blank(value)


class GenerationJobRead(BaseModel):
    job_id: str
    provider: str
    job_type: str
    project_id: str
    chapter_id: str
    shot_id: str
    prompt_revision_id: str
    provider_job_id: str
    provider_result_id: str
    internal_status: str
    ui_status: str
    idempotency_key: str
    request_hash: str
    request_object_id: str
    response_object_id: str
    attempt_number: int
    error_code: str
    error_message: str
    submitted_at: str
    next_poll_at: str
    completed_at: str
    created_at: str
    updated_at: str


class GenerationJobDetailRead(GenerationJobRead):
    request: dict[str, Any]
