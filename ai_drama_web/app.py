import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ai_drama_runtime.store import RuntimeStore

from .config import Settings
from .providers.factory import create_generation_backend
from .middleware.local_management import is_local_management_request, is_management_path
from .routers.asset_delivery import router as asset_delivery_router
from .routers.asset_requirements import router as asset_requirements_router
from .routers.assets import router as assets_router
from .routers.generation import router as generation_router
from .routers.model_bindings import router as model_bindings_router
from .routers.models import router as models_router
from .routers.profiles import router as profiles_router
from .routers.projects import router as projects_router
from .routers.scripts import router as scripts_router
from .routers.settings import router as settings_router
from .routers.suppliers import router as suppliers_router
from .routers.shot_prompts import router as shot_prompts_router
from .routers.storyboards import router as storyboards_router
from .secrets import LocalSecretStore
from .services.asset_delivery import AssetDeliveryService
from .services.generation_execution import GenerationExecutionService
from .services.generation_poller import GenerationPoller
from .services.m6_generation import M6GenerationCoordinator
from .services.legacy_agnes_backfill import LegacyAgnesBackfill
from .suppliers.execution import SnapshotExecutionGateway
from .suppliers.builtin_adapters import install_builtin_adapters
from .store import ProductStore
from .suppliers.credentials import SupplierCredentialStore

DEFAULT_MAX_ASSET_UPLOAD_BYTES = 10 * 1024 * 1024


def create_app(
    *, data_root: Path | None = None, skills_root: str | Path | None = None
) -> FastAPI:
    repo_root = Path(__file__).resolve().parents[1]
    settings = Settings()
    if data_root is not None:
        settings.data_root = Path(data_root)
    if skills_root is not None:
        settings.skills_root = Path(skills_root)
    if not settings.skills_root.is_absolute():
        settings.skills_root = (repo_root / settings.skills_root).resolve()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_store = RuntimeStore(settings.data_root / "runtime.db", settings.data_root / "objects")
        app.state.runtime_store = runtime_store
        product_store = ProductStore(runtime_store)
        app.state.product_store = product_store
        app.state.supplier_credential_store = SupplierCredentialStore(
            product_store, settings.data_root
        )
        app.state.supplier_credential_recovery = app.state.supplier_credential_store.recover()
        supplier_gateway = SnapshotExecutionGateway(product_store, app.state.supplier_credential_store)
        app.state.m6_generation_coordinator = M6GenerationCoordinator(
            product_store, runtime_store, app.state.supplier_credential_store, supplier_gateway
        )
        if settings.m6_supplier_execution_enabled:
            app.state.m6_builtin_adapter_install_count = install_builtin_adapters(product_store)
            app.state.legacy_agnes_backfill_count = LegacyAgnesBackfill(
                product_store, runtime_store, settings.data_root, app.state.secret_store, settings
            ).run()
        if getattr(app.state, "generation_backend", None) is None:
            try:
                app.state.generation_backend = create_generation_backend(settings, app.state.secret_store)
            except RuntimeError as exc:
                if not str(exc).startswith("unsupported runtime provider:"):
                    raise
                app.state.generation_backend = None
        if app.state.generation_backend is not None:
            asset_delivery = AssetDeliveryService(
                product_store,
                runtime_store,
                app.state.secret_store,
                public_base_url=settings.public_base_url,
            )
            execution_service = GenerationExecutionService(
                product_store,
                runtime_store,
                app.state.generation_backend,
                asset_delivery=asset_delivery,
                supplier_gateway=supplier_gateway,
                supplier_execution_enabled=settings.m6_supplier_execution_enabled,
            )
            execution_service.recover_submission_attempts()
            if settings.m6_supplier_execution_enabled:
                app.state.m6_generation_coordinator.recover_image_jobs()
            app.state.generation_poller = GenerationPoller(
                product_store,
                runtime_store,
                app.state.generation_backend,
                rpm=settings.agnes_video_rpm,
                poll_interval_seconds=settings.agnes_poll_interval_seconds,
                execution_service=execution_service,
            )
            await app.state.generation_poller.start()
        else:
            app.state.generation_poller = None
        try:
            yield
        finally:
            if app.state.generation_poller is not None:
                await app.state.generation_poller.stop()
            runtime_store.close()

    app = FastAPI(title="AI Drama Web Production MVP", lifespan=lifespan)
    app.state.settings = settings
    app.state.repo_root = repo_root
    app.state.max_asset_upload_bytes = _max_asset_upload_bytes_from_env()
    app.state.secret_store = LocalSecretStore(settings.data_root)

    @app.middleware("http")
    async def local_management_guard(request, call_next):
        if is_management_path(request.url.path) and not is_local_management_request(
            request, settings.trusted_management_proxy_cidrs
        ):
            return JSONResponse(
                status_code=403,
                content={
                    "error_code": "LOCAL_MANAGEMENT_ONLY",
                    "error_message": "supplier and project model management is available only from the local machine",
                },
            )
        return await call_next(request)

    app.include_router(asset_delivery_router)
    app.include_router(projects_router)
    app.include_router(asset_requirements_router)
    app.include_router(assets_router)
    app.include_router(generation_router)
    app.include_router(models_router)
    app.include_router(model_bindings_router)
    app.include_router(profiles_router)
    app.include_router(scripts_router)
    app.include_router(shot_prompts_router)
    app.include_router(storyboards_router)
    app.include_router(settings_router)
    app.include_router(suppliers_router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request, exc: RequestValidationError):
        safe_errors = []
        for error in exc.errors():
            safe_error = {key: value for key, value in error.items() if key not in {"ctx", "input"}}
            safe_errors.append(safe_error)
        return JSONResponse(status_code=422, content={"detail": safe_errors})

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def _max_asset_upload_bytes_from_env() -> int:
    raw_value = os.getenv("AI_DRAMA_MAX_ASSET_UPLOAD_BYTES")
    if raw_value is None:
        return DEFAULT_MAX_ASSET_UPLOAD_BYTES
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_MAX_ASSET_UPLOAD_BYTES
    return value if value > 0 else DEFAULT_MAX_ASSET_UPLOAD_BYTES


def main() -> None:
    import uvicorn

    uvicorn.run(
        "ai_drama_web.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        access_log=False,
    )
