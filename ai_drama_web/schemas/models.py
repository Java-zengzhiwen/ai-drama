from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SupplierModelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_model_name: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    capability: Literal["text", "image", "video"]
    definition: dict = Field(default_factory=dict)


class SupplierModelPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_model_name: str | None = Field(default=None, min_length=1, max_length=200)
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    capability: Literal["text", "image", "video"] | None = None
    definition: dict | None = None
    enabled: bool | None = None
    acknowledged_binding_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def one_mutation_kind(self):
        semantic = any(
            value is not None
            for value in (
                self.provider_model_name,
                self.display_name,
                self.capability,
                self.definition,
            )
        )
        if self.enabled is not None and semantic:
            raise ValueError("enabled and semantic fields must be updated separately")
        if self.enabled is None and not semantic:
            raise ValueError("at least one model field is required")
        return self


class ProjectModelBindingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    defaults: dict[Literal["text", "image", "video"], str]
    operation_overrides: dict[str, str] = Field(default_factory=dict)
