"""
Product CRUD endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.storage import generate_presigned_url, upload_image
from app.models.user import User
from app.models.image import ProductImage
from app.schemas.product import (
    ProductCreate,
    ProductImageResponse,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
    ProductExtractRequest,
    ProductExtractResponse,
)
from app.services.ingestion import extract_from_url
from app.services.catalog import (
    create_product,
    delete_product,
    get_product,
    list_products,
    update_product,
)

router = APIRouter(prefix="/products", tags=["Products"])


def _product_to_response(product) -> ProductResponse:
    """Convert a Product ORM object to a ProductResponse schema."""
    images = []
    for img in (product.images or []):
        try:
            if img.s3_key.startswith(("http://", "https://")):
                url = img.s3_key
            else:
                url = generate_presigned_url(img.s3_key)
        except Exception:
            url = ""
        images.append(ProductImageResponse(
            id=str(img.id),
            url=url,
            position=img.position,
        ))

    return ProductResponse(
        id=str(product.id),
        title=product.title,
        description=product.description,
        brand=product.brand,
        category_id=str(product.category_id) if product.category_id else None,
        category_name=product.category.name if product.category else None,
        price_current=float(product.price_current) if product.price_current else None,
        currency=product.currency,
        store=product.store,
        source=product.source,
        source_url=product.source_url,
        status=product.status.value,
        priority=product.priority,
        rating=float(product.rating) if product.rating else None,
        notes=product.notes,
        is_favorite=product.is_favorite,
        is_purchased=product.is_purchased,
        tags=[t.name for t in (product.tags or [])],
        collections=[
            {"id": str(c.id), "name": c.name, "emoji": c.emoji}
            for c in (product.collections or [])
        ],
        images=images,
        saved_at=product.saved_at.isoformat(),
        updated_at=product.updated_at.isoformat(),
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Save a new product",
)
async def save_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a product from a URL or manual entry.
    Returns 202 Accepted — the product may still be processing (async enrichment).
    """
    try:
        product = await create_product(db, current_user.id, data)
        product = await get_product(db, current_user.id, product.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return _product_to_response(product)


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List saved products",
)
async def list_my_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: UUID | None = None,
    is_favorite: bool | None = None,
    is_purchased: bool | None = None,
    sort_by: str = Query("saved_at", regex="^(saved_at|price_current|title|priority)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the authenticated user's products with filters and pagination."""
    products, total = await list_products(
        db, current_user.id,
        page=page, page_size=page_size,
        category_id=category_id,
        is_favorite=is_favorite,
        is_purchased=is_purchased,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ProductListResponse(
        items=[_product_to_response(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size < total),
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details",
)
async def get_product_detail(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full details of a saved product."""
    product = await get_product(db, current_user.id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _product_to_response(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
)
async def update_product_endpoint(
    product_id: UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update product fields (partial update)."""
    product = await update_product(db, current_user.id, product_id, data)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _product_to_response(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product",
)
async def delete_product_endpoint(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a product."""
    deleted = await delete_product(db, current_user.id, product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.post(
    "/{product_id}/favorite",
    response_model=ProductResponse,
    summary="Toggle favorite",
)
async def toggle_favorite(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle a product's favorite status."""
    product = await get_product(db, current_user.id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.is_favorite = not product.is_favorite
    await db.flush()
    return _product_to_response(product)


@router.post(
    "/{product_id}/purchased",
    response_model=ProductResponse,
    summary="Toggle purchase status",
)
async def toggle_purchased(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle a product's purchased status."""
    product = await get_product(db, current_user.id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product.is_purchased = not product.is_purchased
    await db.flush()
    return _product_to_response(product)


@router.post(
    "/{product_id}/images",
    status_code=status.HTTP_201_CREATED,
    summary="Upload an image for a product",
)
async def upload_product_image(
    product_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = await get_product(db, current_user.id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    content = await file.read()
    content_type = file.content_type or "image/jpeg"

    try:
        s3_key = upload_image(content, content_type)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to upload image: {str(e)}")

    pos = len(product.images)
    db_img = ProductImage(
        product_id=product.id,
        s3_key=s3_key,
        position=pos,
    )
    db.add(db_img)
    await db.flush()

    return {"message": "Image uploaded successfully", "s3_key": s3_key}


@router.post(
    "/extract",
    response_model=ProductExtractResponse,
    summary="Extract product metadata from a URL live",
)
async def extract_product_metadata(
    data: ProductExtractRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Extract product metadata (title, price, store, images) from the URL live.
    This can be called by the frontend during product creation to show a preview.
    """
    try:
        extraction = await extract_from_url(data.url)
        return ProductExtractResponse(
            title=extraction.title,
            description=extraction.description,
            brand=extraction.brand,
            price=extraction.price,
            currency=extraction.currency or "INR",
            store=extraction.store,
            source=extraction.source,
            image_urls=extraction.image_urls or []
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract metadata: {str(e)}"
        )
