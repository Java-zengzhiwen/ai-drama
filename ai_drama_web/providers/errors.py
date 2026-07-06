from copy import deepcopy
from typing import Any


class ProviderError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        provider: str,
        raw: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(f"{provider} provider error [{code}]: {message}")
        self.code = code
        self.provider = provider
        self.raw = deepcopy(raw or {})
