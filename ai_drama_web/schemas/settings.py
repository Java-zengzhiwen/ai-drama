from pydantic import BaseModel, ConfigDict, field_validator


class AgnesSettingsRead(BaseModel):
    configured: bool
    masked_suffix: str


class AgnesSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: str

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        if len(value.strip()) < 8:
            raise ValueError("must be at least 8 characters")
        return value
