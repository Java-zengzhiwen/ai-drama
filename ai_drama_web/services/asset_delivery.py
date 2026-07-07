import hmac
import time
from hashlib import sha256
from urllib.parse import quote

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore


class AssetDeliveryForbidden(Exception):
    pass


class AssetDeliveryUnsupportedMediaType(Exception):
    pass


class AssetDeliveryInvalidPublicBaseUrl(Exception):
    pass


class AssetDeliveryService:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        secret_store: LocalSecretStore,
        *,
        public_base_url: str,
    ) -> None:
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.secret_store = secret_store
        self.public_base_url = public_base_url.rstrip("/")

    def signed_asset_url(self, asset_id: str, *, ttl_seconds: int = 900) -> str:
        self._require_provider_reachable_base_url()
        expires = int(time.time()) + ttl_seconds
        signature = self.sign(asset_id, expires)
        return "%s/public/assets/%s?expires=%s&signature=%s" % (
            self.public_base_url,
            quote(asset_id, safe=""),
            expires,
            signature,
        )

    def public_asset_content(self, asset_id: str, *, expires: int, signature: str):
        if expires < int(time.time()):
            raise AssetDeliveryForbidden
        expected = self.sign(asset_id, expires)
        if not hmac.compare_digest(expected, signature):
            raise AssetDeliveryForbidden
        asset = self.product_store.get_asset(asset_id)
        if asset is None:
            raise MissingRecord
        if not asset.media_type.startswith("image/"):
            raise AssetDeliveryUnsupportedMediaType
        return self.runtime_store.read_bytes_object(asset.object_id), asset.media_type

    def sign(self, asset_id: str, expires: int) -> str:
        payload = f"{asset_id}.{expires}"
        return hmac.new(
            self.secret_store.get_asset_delivery_secret().encode("utf-8"),
            payload.encode("utf-8"),
            sha256,
        ).hexdigest()

    def _require_provider_reachable_base_url(self) -> None:
        normalized = self.public_base_url.lower()
        if not normalized.startswith("https://"):
            raise AssetDeliveryInvalidPublicBaseUrl
        blocked_fragments = ("localhost", "127.0.0.1", "[::1]")
        if any(fragment in normalized for fragment in blocked_fragments):
            raise AssetDeliveryInvalidPublicBaseUrl
