from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import Response

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.dependencies import get_product_store, get_runtime_store
from ai_drama_web.secrets import LocalSecretStore
from ai_drama_web.services.asset_delivery import (
    AssetDeliveryForbidden,
    AssetDeliveryService,
    AssetDeliveryUnsupportedMediaType,
)
from ai_drama_web.services.projects import MissingRecord
from ai_drama_web.store import ProductStore

router = APIRouter()


def get_secret_store(request: Request) -> LocalSecretStore:
    return request.app.state.secret_store


def get_public_base_url(request: Request) -> str:
    return request.app.state.settings.public_base_url


def get_service(
    product_store: ProductStore = Depends(get_product_store),
    runtime_store: RuntimeStore = Depends(get_runtime_store),
    secret_store: LocalSecretStore = Depends(get_secret_store),
    public_base_url: str = Depends(get_public_base_url),
) -> AssetDeliveryService:
    return AssetDeliveryService(
        product_store,
        runtime_store,
        secret_store,
        public_base_url=public_base_url,
    )


@router.get("/public/assets/{asset_id}")
async def public_asset_content(
    asset_id: str,
    expires: int,
    signature: str,
    service: AssetDeliveryService = Depends(get_service),
):
    try:
        content, media_type = service.public_asset_content(
            asset_id,
            expires=expires,
            signature=signature,
        )
    except AssetDeliveryForbidden:
        raise HTTPException(status_code=403, detail="invalid or expired asset signature")
    except MissingRecord:
        raise HTTPException(status_code=404, detail="asset not found")
    except AssetDeliveryUnsupportedMediaType:
        raise HTTPException(status_code=415, detail="only image assets can be delivered")
    return Response(content=content, media_type=media_type)
