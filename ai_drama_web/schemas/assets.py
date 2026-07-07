from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

AssetType = Literal[
    "character_reference",
    "character_outfit",
    "scene_reference",
    "scene_angle",
    "prop_reference",
    "shot_keyframe",
]
AssetStatus = Literal["draft", "generating", "usable", "rejected", "failed"]
AssetSourceType = Literal["upload", "agnes", "derived"]
BindingTargetType = Literal["character", "scene", "prop", "shot"]


def _not_blank(value: str) -> str:
    if not value.strip():
        raise ValueError("must not be blank")
    return value


class AssetUploadFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: AssetType
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _not_blank(value)


class AssetGenerateImageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_type: AssetType
    name: str
    prompt: str
    size: str
    input_asset_ids: list[str] = Field(default_factory=list)
    input_images: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "prompt", "size")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _not_blank(value)

    @field_validator("input_asset_ids", "input_images")
    @classmethod
    def validate_list_items(cls, value: list[str]) -> list[str]:
        for item in value:
            _not_blank(item)
        return value


class AssetBindingCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: BindingTargetType
    target_id: str
    role: str
    is_current: bool = False

    @field_validator("target_id", "role")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        return _not_blank(value)


class AssetRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = ""

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        if value and not value.strip():
            raise ValueError("must not be blank")
        return value


class AssetBindingRead(BaseModel):
    binding_id: str
    asset_id: str
    target_type: BindingTargetType
    target_id: str
    role: str
    is_current: bool
    created_at: str


class AssetRead(BaseModel):
    asset_id: str
    project_id: str
    chapter_id: str
    asset_type: AssetType
    name: str
    object_id: str
    media_type: str
    width: int
    height: int
    status: AssetStatus
    source_type: AssetSourceType
    source_job_id: str
    metadata: dict[str, Any]
    bindings: list[AssetBindingRead] = Field(default_factory=list)
    created_at: str
    updated_at: str
