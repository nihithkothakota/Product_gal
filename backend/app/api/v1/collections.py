"""
Collection CRUD endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.collection import Collection, ProductCollection
from app.models.user import User
from app.schemas.collection import (
    AddProductToCollection,
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
)
from app.services.catalog import (
    add_product_to_collection,
    create_collection,
    get_collection,
    list_collections,
)

router = APIRouter(prefix="/collections", tags=["Collections"])


def _collection_to_response(collection: Collection, product_count: int = 0) -> CollectionResponse:
    """Convert a Collection ORM object to a response schema."""
    return CollectionResponse(
        id=str(collection.id),
        name=collection.name,
        emoji=collection.emoji,
        description=collection.description,
        is_public=collection.is_public,
        share_code=collection.share_code,
        parent_id=str(collection.parent_id) if collection.parent_id else None,
        product_count=product_count,
        children=[
            _collection_to_response(c) for c in (collection.children or [])
        ],
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat(),
    )


@router.post(
    "",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
async def create_collection_endpoint(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new collection (folder) for organizing products."""
    collection = await create_collection(
        db, current_user.id,
        name=data.name,
        emoji=data.emoji,
        description=data.description,
        parent_id=data.parent_id,
        is_public=data.is_public,
    )
    # Re-fetch with relationships eagerly loaded to avoid MissingGreenlet on async driver
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.children))
        .where(Collection.id == collection.id)
    )
    collection = result.scalar_one()
    count_result = await db.execute(
        select(func.count()).where(ProductCollection.collection_id == collection.id)
    )
    return _collection_to_response(collection, product_count=count_result.scalar_one())


@router.get(
    "",
    response_model=CollectionListResponse,
    summary="List collections",
)
async def list_collections_endpoint(
    parent_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the user's collections. Optionally filter by parent for nested navigation."""
    collections = await list_collections(db, current_user.id, parent_id=parent_id)

    # Get product counts
    items = []
    for coll in collections:
        count_result = await db.execute(
            select(func.count()).where(ProductCollection.collection_id == coll.id)
        )
        count = count_result.scalar_one()
        items.append(_collection_to_response(coll, product_count=count))

    return CollectionListResponse(items=items, total=len(items))


@router.get(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Get collection details",
)
async def get_collection_endpoint(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a collection with its products."""
    collection = await get_collection(db, current_user.id, collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    count_result = await db.execute(
        select(func.count()).where(ProductCollection.collection_id == collection.id)
    )
    count = count_result.scalar_one()

    from app.api.v1.products import _product_to_response
    res = _collection_to_response(collection, product_count=count)
    res.products = [_product_to_response(p) for p in (collection.products or []) if not p.is_deleted]
    return res


@router.put(
    "/{collection_id}",
    response_model=CollectionResponse,
    summary="Update a collection",
)
async def update_collection_endpoint(
    collection_id: UUID,
    data: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update collection name, emoji, visibility, etc."""
    collection = await get_collection(db, current_user.id, collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)

    await db.flush()
    # Re-fetch to ensure relationships are loaded
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.children))
        .where(Collection.id == collection.id)
    )
    collection = result.scalar_one()
    count_result = await db.execute(
        select(func.count()).where(ProductCollection.collection_id == collection.id)
    )
    return _collection_to_response(collection, product_count=count_result.scalar_one())


@router.delete(
    "/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a collection",
)
async def delete_collection_endpoint(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a collection (products remain, just removed from this collection)."""
    collection = await get_collection(db, current_user.id, collection_id)
    if not collection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    await db.delete(collection)
    await db.flush()


@router.post(
    "/{collection_id}/products",
    status_code=status.HTTP_201_CREATED,
    summary="Add product to collection",
)
async def add_product_endpoint(
    collection_id: UUID,
    data: AddProductToCollection,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a product to a collection."""
    success = await add_product_to_collection(
        db, current_user.id, collection_id, data.product_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection or product not found",
        )
    return {"message": "Product added to collection"}


@router.delete(
    "/{collection_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove product from collection",
)
async def remove_product_from_collection(
    collection_id: UUID,
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a product from a collection (doesn't delete the product)."""
    result = await db.execute(
        select(ProductCollection).where(
            ProductCollection.product_id == product_id,
            ProductCollection.collection_id == collection_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not in collection")
    await db.delete(link)
    await db.flush()
