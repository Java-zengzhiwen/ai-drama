from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

ProfileType = Literal["character", "scene", "prop", "style"]


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


def _not_blank_when_present(value: str) -> str:
    if value and not value.strip():
        raise ValueError("must not be blank")
    return value


class BaseProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    continuity_notes: str

    @field_validator("name", "continuity_notes")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _not_blank(value)


class CharacterProfilePayload(BaseProfilePayload):
    identity_notes: str = ""
    appearance_notes: str = ""
    costume_notes: str

    @field_validator("identity_notes", "appearance_notes")
    @classmethod
    def validate_optional_text(cls, value: str) -> str:
        return _not_blank_when_present(value)

    @field_validator("costume_notes")
    @classmethod
    def validate_costume_notes(cls, value: str) -> str:
        return _not_blank(value)

    @model_validator(mode="after")
    def validate_identity_or_appearance(self):
        if not self.identity_notes.strip() and not self.appearance_notes.strip():
            raise ValueError("identity_notes or appearance_notes is required")
        return self


class SceneProfilePayload(BaseProfilePayload):
    scene_layout_notes: str
    lighting_notes: str

    @field_validator("scene_layout_notes", "lighting_notes")
    @classmethod
    def validate_scene_text(cls, value: str) -> str:
        return _not_blank(value)


class PropProfilePayload(BaseProfilePayload):
    prop_handling_notes: str

    @field_validator("prop_handling_notes")
    @classmethod
    def validate_prop_text(cls, value: str) -> str:
        return _not_blank(value)


class StyleProfilePayload(BaseProfilePayload):
    style_rules: str
    cinematography_rules: str
    color_rules: str
    negative_rules: str

    @field_validator("style_rules", "cinematography_rules", "color_rules", "negative_rules")
    @classmethod
    def validate_style_text(cls, value: str) -> str:
        return _not_blank(value)


PAYLOAD_MODELS = {
    "character": CharacterProfilePayload,
    "scene": SceneProfilePayload,
    "prop": PropProfilePayload,
    "style": StyleProfilePayload,
}


def validate_profile_payload(profile_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    model = PAYLOAD_MODELS[profile_type]
    return model.model_validate(payload).model_dump(mode="json")


class ProductionProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chapter_id: str = ""
    profile_type: ProfileType
    payload: dict[str, Any]

    @field_validator("chapter_id")
    @classmethod
    def validate_chapter_id(cls, value: str) -> str:
        if value and not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def validate_payload(self):
        self.payload = validate_profile_payload(self.profile_type, self.payload)
        return self


class ProductionProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: dict[str, Any]


class ProductionProfileRead(BaseModel):
    profile_id: str
    project_id: str
    chapter_id: str
    profile_type: ProfileType
    name: str
    payload: dict[str, Any]
    created_at: str
    updated_at: str
