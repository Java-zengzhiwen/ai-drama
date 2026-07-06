from fastapi import APIRouter, Depends, Request

from ai_drama_web.schemas.settings import AgnesSettingsRead, AgnesSettingsUpdate
from ai_drama_web.secrets import LocalSecretStore

router = APIRouter(prefix="/api/settings")


def get_secret_store(request: Request) -> LocalSecretStore:
    return request.app.state.secret_store


@router.get("/agnes", response_model=AgnesSettingsRead)
def get_agnes_settings(secret_store: LocalSecretStore = Depends(get_secret_store)):
    return secret_store.agnes_status()


@router.put("/agnes", response_model=AgnesSettingsRead)
def put_agnes_settings(
    payload: AgnesSettingsUpdate,
    secret_store: LocalSecretStore = Depends(get_secret_store),
):
    secret_store.set_agnes_api_key(payload.api_key)
    return secret_store.agnes_status()


@router.delete("/agnes", response_model=AgnesSettingsRead)
def delete_agnes_settings(secret_store: LocalSecretStore = Depends(get_secret_store)):
    secret_store.delete_agnes_api_key()
    return secret_store.agnes_status()
