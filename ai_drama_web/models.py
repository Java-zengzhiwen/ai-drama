from dataclasses import dataclass


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
