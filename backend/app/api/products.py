"""Routes CRUD des produits."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/status", status_code=status.HTTP_200_OK)
async def products_status() -> dict[str, str]:
    return {"message": "Product routes are ready"}

@router.get("/", response_model=list[ProductRead])
async def list_products(current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)], limit: int = 50, offset: int = 0, category: str | None = None, search: str | None = None):
    return await ProductService(db).list_products(limit=min(limit, 100), offset=offset, category=category, search=search)

@router.get("/{product_id}", response_model=ProductRead)
async def get_product(product_id: UUID, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    product = await ProductService(db).get_product(product_id)
    if product is None: raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/", response_model=ProductRead, status_code=201)
async def create_product(payload: ProductCreate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    return await ProductService(db).create_product(payload)

@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(product_id: UUID, payload: ProductUpdate, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    product = await ProductService(db).update_product(product_id, payload)
    if product is None: raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: UUID, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db_session)]):
    if await ProductService(db).get_product(product_id) is None: raise HTTPException(status_code=404, detail="Product not found")
    await ProductService(db).delete_product(product_id)

__all__ = ["router"]
