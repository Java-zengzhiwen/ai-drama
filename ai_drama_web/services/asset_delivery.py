import hmac
import ipaddress
import time
from hashlib import sha256
from urllib.parse import quote, urlparse

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
        if ttl_seconds < 1 or ttl_seconds > 3600:
            raise ValueError("ttl_seconds must be between 1 and 3600")
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
        parsed = urlparse(self.public_base_url)
        if parsed.scheme != "https":
            raise AssetDeliveryInvalidPublicBaseUrl
        if parsed.username or parsed.password:
            raise AssetDeliveryInvalidPublicBaseUrl
        hostname = parsed.hostname
        if not hostname:
            raise AssetDeliveryInvalidPublicBaseUrl
        if hostname.lower() == "localhost":
            raise AssetDeliveryInvalidPublicBaseUrl
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            return
        if (
            address.is_loopback
            or address.is_private
            or address.is_link_local
            or address.is_reserved
            or address.is_unspecified
        ):
            raise AssetDeliveryInvalidPublicBaseUrl
