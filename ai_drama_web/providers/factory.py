from ai_drama_web.config import Settings
from ai_drama_web.providers.agnes import AgnesImageBackend
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.secrets import LocalSecretStore


def create_generation_backend(settings: Settings, secret_store: LocalSecretStore) -> GenerationBackend:
    provider = settings.runtime_provider.strip().lower()
    if provider == "mock":
        backend_cls = FakeGenerationBackend
        backend = backend_cls()
        return backend
    if provider == "agnes":
        api_key = secret_store.get_agnes_api_key().strip()
        if not api_key:
            raise RuntimeError("Agnes API key is not configured")
        return AgnesImageBackend(
            api_key,
            video_endpoint=settings.agnes_video_endpoint,
            video_status_endpoint=settings.agnes_video_status_endpoint,
            video_model=settings.agnes_video_model,
            timeout_seconds=settings.agnes_timeout_seconds,
        )
    raise RuntimeError(f"unsupported runtime provider: {settings.runtime_provider}")
