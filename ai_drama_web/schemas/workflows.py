from pydantic import BaseModel, ConfigDict, field_validator


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class ErrorResponse(BaseModel):
    error_code: str
    error_message: str


class ValidationResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    validation_id: str
    validator_id: str
    status: str
    required: bool
    error_code: str


class ScriptRevisionRead(BaseModel):
    revision_id: str
    artifact_id: str
    chapter_id: str
    number: int
    approval_status: str
    current: bool
    content: str
    validation_results: list[ValidationResultRead]


class ScriptRevisionUpdate(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        return _not_blank(value)


class RevisionDecision(BaseModel):
    reviewer: str = "local-user"
    note: str = ""

    @field_validator("reviewer")
    @classmethod
    def validate_reviewer(cls, value: str) -> str:
        return _not_blank(value)
