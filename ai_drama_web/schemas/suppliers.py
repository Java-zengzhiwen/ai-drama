from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")
    display_name: str = Field(min_length=1, max_length=120)


class SupplierUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    enabled: bool | None = None


class SupplierConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[str, str]


class SupplierSecretUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    credential: str = Field(min_length=8, max_length=16384)


class SupplierCodeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1, max_length=1024 * 1024)
