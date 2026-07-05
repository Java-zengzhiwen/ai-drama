from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from ai_drama_runtime.store import RuntimeStore

from .config import Settings
from .routers.projects import router as projects_router
from .routers.scripts import router as scripts_router
from .store import ProductStore


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
    app.include_router(projects_router)
    app.include_router(scripts_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(
        "ai_drama_web.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
    )
