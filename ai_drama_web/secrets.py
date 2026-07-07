import os
import secrets
import tempfile
from pathlib import Path


class LocalSecretStore:
    def __init__(self, data_root: Path):
        self._secret_path = Path(data_root) / "secrets" / "agnes-api-key"
        self._asset_delivery_secret_path = Path(data_root) / "secrets" / "asset-delivery-signing-secret"

    def set_agnes_api_key(self, value: str) -> None:
        self._write_secret_file(self._secret_path, value)

    def get_agnes_api_key(self) -> str:
        if not self._secret_path.exists():
            return ""
        return self._secret_path.read_text(encoding="utf-8")

    def delete_agnes_api_key(self) -> None:
        self._secret_path.unlink(missing_ok=True)

    def agnes_status(self) -> dict[str, object]:
        api_key = self.get_agnes_api_key()
        if not api_key:
            return {"configured": False, "masked_suffix": ""}
        if len(api_key) <= 4:
            return {"configured": True, "masked_suffix": ""}
        return {"configured": True, "masked_suffix": api_key[-4:]}

    def get_asset_delivery_secret(self) -> str:
        if self._asset_delivery_secret_path.exists():
            return self._asset_delivery_secret_path.read_text(encoding="utf-8")
        value = secrets.token_urlsafe(32)
        self._write_secret_file(self._asset_delivery_secret_path, value)
        return value

    def _write_secret_file(self, path: Path, value: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            text=True,
        )
        temp_path = Path(temp_name)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as temp_file:
                temp_file.write(value)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, path)
            os.chmod(path, 0o600)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            temp_path.unlink(missing_ok=True)
            raise
