from dataclasses import dataclass


@dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    project_id: str
    chapter_id: str
    asset_type: str
    name: str
    object_id: str
    media_type: str
    width: int
    height: int
    status: str
    source_type: str
    source_job_id: str
    metadata_object_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AssetBindingRecord:
    binding_id: str
    asset_id: str
    project_id: str
    chapter_id: str
    target_type: str
    target_id: str
    role: str
    is_current: int
    created_at: str


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    name: str
    description: str
    series_canon: str
    characters_context: str
    production_brief: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChapterRecord:
    chapter_id: str
    project_id: str
    title: str
    position: int
    current_source_revision_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChapterSourceRevisionRecord:
    source_revision_id: str
    chapter_id: str
    number: int
    object_id: str
    content_hash: str
    created_at: str


@dataclass(frozen=True)
class ProductionProfileRecord:
    profile_id: str
    project_id: str
    chapter_id: str
    profile_type: str
    name: str
    payload_object_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class GenerationJobRecord:
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


@dataclass(frozen=True)
class GenerationResultRecord:
    result_id: str
    job_id: str
    chapter_id: str
    shot_id: str
    object_id: str
    media_type: str
    source_url: str
    metadata_object_id: str
    created_at: str


@dataclass(frozen=True)
class ShotResultSelectionRecord:
    chapter_id: str
    shot_id: str
    result_id: str
    selected_at: str


@dataclass(frozen=True)
class ResultReviewRecord:
    review_id: str
    result_id: str
    decision: str
    failure_category: str
    note: str
    created_at: str


@dataclass(frozen=True)
class RerunRecord:
    rerun_id: str
    source_job_id: str
    new_job_id: str
    overrides_object_id: str
    created_at: str
