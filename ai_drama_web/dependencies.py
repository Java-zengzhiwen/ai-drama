from fastapi import Request

from ai_drama_runtime.store import RuntimeStore

from .store import ProductStore


def get_runtime_store(request: Request) -> RuntimeStore:
    return request.app.state.runtime_store


def get_product_store(request: Request) -> ProductStore:
    return request.app.state.product_store
