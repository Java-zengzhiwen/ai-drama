import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ai_drama_runtime.store import RuntimeStore

from .config import Settings
from .routers.asset_delivery import router as asset_delivery_router
from .routers.asset_requirements import router as asset_requirements_router
from .routers.assets import router as assets_router
from .routers.generation import router as generation_router
from .routers.profiles import router as profiles_router
from .routers.projects import router as projects_router
from .routers.scripts import router as scripts_router
from .routers.settings import router as settings_router
from .routers.shot_prompts import router as shot_prompts_router
from .routers.storyboards import router as storyboards_router
from .secrets import LocalSecretStore
from .store import ProductStore

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
        app.state.product_store = ProductStore(runtime_store)
        try:
            yield
        finally:
            runtime_store.close()

    app = FastAPI(title="AI Drama Web Production MVP", lifespan=lifespan)
    app.state.settings = settings
    app.state.repo_root = repo_root
    app.state.max_asset_upload_bytes = _max_asset_upload_bytes_from_env()
    app.state.secret_store = LocalSecretStore(settings.data_root)
    app.include_router(asset_delivery_router)
    app.include_router(projects_router)
    app.include_router(asset_requirements_router)
    app.include_router(assets_router)
    app.include_router(generation_router)
    app.include_router(profiles_router)
    app.include_router(scripts_router)
    app.include_router(shot_prompts_router)
    app.include_router(storyboards_router)
    app.include_router(settings_router)

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
    )
