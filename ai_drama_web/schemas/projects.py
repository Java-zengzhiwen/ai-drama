from pydantic import BaseModel, ConfigDict, Field, field_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    series_canon: str = ""
    characters_context: str = ""
    production_brief: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _not_blank(value)


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    name: str
    description: str
    series_canon: str
    characters_context: str
    production_brief: str
    created_at: str
    updated_at: str


class ChapterCreate(BaseModel):
    title: str
    position: int = Field(ge=1)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _not_blank(value)


class ChapterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    project_id: str
    title: str
    position: int
    current_source_revision_id: str
    created_at: str
    updated_at: str
    source_text: str = ""


class SourceRevisionCreate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _not_blank(value)


class SourceRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_revision_id: str
    chapter_id: str
    number: int
    object_id: str
    content_hash: str
    created_at: str
