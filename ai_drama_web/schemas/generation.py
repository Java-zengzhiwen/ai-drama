from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class VideoJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_revision_id: str
    shot_id: str
    idempotency_key: str

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


class GenerationResultRead(BaseModel):
    result_id: str
    job_id: str
    attempt_number: int
    media_type: str
    source_url: str
    source_url_state: str = "source_url_active"
    local_result_available: bool
    local_content_url: str = ""
    created_at: str


class ShotResultsRead(BaseModel):
    shot_id: str
    current_result_id: str
    results: list[GenerationResultRead]


class ShotResultSelectionRead(BaseModel):
    chapter_id: str
    shot_id: str
    result_id: str
    selected_at: str


class ResultReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["passed", "failed"]
    failure_category: str = ""
    note: str = ""

    @model_validator(mode="after")
    def validate_failure_category(self):
        allowed = {
            "authentication",
            "rate_limited",
            "invalid_request",
            "input_unreachable",
            "provider_busy",
            "generation_failed",
            "timeout",
            "result_expired",
            "unknown_provider_error",
            "submission_outcome_unknown",
        }
        if self.decision == "passed" and self.failure_category:
            raise ValueError("passed review must not include failure_category")
        if self.decision == "failed" and self.failure_category not in allowed:
            raise ValueError("failed review requires a stable failure_category")
        return self


class ResultReviewRead(BaseModel):
    review_id: str
    result_id: str
    decision: str
    failure_category: str
    note: str
    created_at: str


class GenerationRerunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str
    prompt: str | None = None
    negative_prompt: str | None = None
    asset_ids: list[str] | None = None
    duration_seconds: int | None = None
    mode: Literal["std", "pro", "keyframes"] | None = None
    seed: int | None = None

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str) -> str:
        return _not_blank(value)


class GenerationRerunRead(BaseModel):
    rerun_id: str
    source_job_id: str
    new_job: GenerationJobRead
    created_at: str
