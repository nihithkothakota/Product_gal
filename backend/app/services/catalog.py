"""
Catalog service — core business logic for products and collections.
Handles CRUD, duplicate detection, and collection management.
"""

from uuid import UUID
import re

import httpx
import structlog
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product, ProductStatus
from app.models.collection import Collection, ProductCollection
from app.models.tag import Tag, ProductTag
from app.models.image import ProductImage
from app.models.category import Category
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.ingestion import extract_from_url, hash_url
from app.core.storage import upload_image, generate_presigned_url

logger = structlog.get_logger()


# ── Products ─────────────────────────────────────────────────────────────

async def create_product(
    db: AsyncSession,
    user_id: UUID,
    data: ProductCreate,
) -> Product:
    """
    Create a new product. If a source_url is provided:
    1. Check for duplicates (URL hash)
    2. Extract metadata from the URL
    3. Create the product with status=processing (or enriched if extraction succeeds)
    """

    # Duplicate detection
    if data.source_url:
        data.source_url = data.source_url.strip()
        if not re.match(r"^https?://", data.source_url, re.IGNORECASE):
            data.source_url = "https://" + data.source_url

        url_hash = hash_url(data.source_url)
        existing = await db.execute(
            select(Product).where(
                and_(
                    Product.user_id == user_id,
                    Product.source_url_hash == url_hash,
                    Product.is_deleted == False,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Product with this URL already saved")

    product = Product(
        user_id=user_id,
        title=data.title,
        description=data.description,
        brand=data.brand,
        category_id=data.category_id,
        price_current=data.price_current,
        currency=data.currency,
        store=data.store,
        source=data.source or "manual",
        source_url=data.source_url,
        source_url_hash=hash_url(data.source_url) if data.source_url else None,
        notes=data.notes,
        priority=data.priority,
        status=ProductStatus.PROCESSING if data.source_url else ProductStatus.ENRICHED,
    )

    db.add(product)
    await db.flush()  # get the product ID

    # Handle tags
    if data.tags:
        await _sync_tags(db, product, data.tags)

    # Handle collections
    if data.collection_ids:
        for coll_id in data.collection_ids:
            db.add(ProductCollection(product_id=product.id, collection_id=coll_id))

    # Handle direct custom image_url if provided
    if hasattr(data, "image_url") and data.image_url:
        try:
            await _download_and_store_images(db, product, [data.image_url])
        except Exception as e:
            logger.warning("direct_image_download_failed", url=data.image_url, error=str(e))

    # URL extraction (Phase 1: synchronous inline)
    if data.source_url:
        try:
            extraction = await extract_from_url(data.source_url)
            product.title = product.title or extraction.title
            product.description = product.description or extraction.description
            product.brand = product.brand or extraction.brand
            product.price_current = product.price_current or extraction.price
            product.currency = extraction.currency or product.currency
            product.store = product.store or extraction.store
            product.source = product.source or extraction.source

            # Download and store images
            if extraction.image_urls:
                await _download_and_store_images(db, product, extraction.image_urls[:5])

            product.status = ProductStatus.ENRICHED
            logger.info("product_enriched_inline", product_id=str(product.id))
        except Exception as e:
            logger.error("product_extraction_failed", error=str(e))
            product.status = ProductStatus.FAILED

    await db.flush()
    return product


async def get_product(db: AsyncSession, user_id: UUID, product_id: UUID) -> Product | None:
    """Get a single product by ID, ensuring ownership."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.tags),
            selectinload(Product.collections),
            selectinload(Product.category),
        )
        .where(
            and_(
                Product.id == product_id,
                Product.user_id == user_id,
                Product.is_deleted == False,
            )
        )
    )
    return result.scalar_one_or_none()


async def list_products(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
    category_id: UUID | None = None,
    is_favorite: bool | None = None,
    is_purchased: bool | None = None,
    sort_by: str = "saved_at",
    sort_order: str = "desc",
) -> tuple[list[Product], int]:
    """List products with filtering and pagination."""
    query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.tags),
            selectinload(Product.collections),
        )
        .where(
            and_(
                Product.user_id == user_id,
                Product.is_deleted == False,
            )
        )
    )

    # Apply filters
    if category_id:
        query = query.where(Product.category_id == category_id)
    if is_favorite is not None:
        query = query.where(Product.is_favorite == is_favorite)
    if is_purchased is not None:
        query = query.where(Product.is_purchased == is_purchased)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Sort
    sort_column = getattr(Product, sort_by, Product.saved_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Paginate
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    products = list(result.scalars().unique().all())

    return products, total


async def update_product(
    db: AsyncSession, user_id: UUID, product_id: UUID, data: ProductUpdate
) -> Product | None:
    """Update a product's fields."""
    product = await get_product(db, user_id, product_id)
    if not product:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # Handle tags separately
    if "tags" in update_data:
        await _sync_tags(db, product, update_data.pop("tags"))

    # Handle collections separately
    if "collection_ids" in update_data:
        collection_ids = update_data.pop("collection_ids")
        # Remove existing
        await db.execute(
            ProductCollection.__table__.delete().where(
                ProductCollection.product_id == product.id
            )
        )
        # Add new
        for coll_id in collection_ids:
            db.add(ProductCollection(product_id=product.id, collection_id=coll_id))

    # Update scalar fields
    for field, value in update_data.items():
        if hasattr(product, field):
            setattr(product, field, value)

    await db.flush()
    return product


async def delete_product(db: AsyncSession, user_id: UUID, product_id: UUID) -> bool:
    """Soft-delete a product."""
    product = await get_product(db, user_id, product_id)
    if not product:
        return False
    product.is_deleted = True
    await db.flush()
    return True


# ── Collections ──────────────────────────────────────────────────────────

async def create_collection(
    db: AsyncSession, user_id: UUID, name: str, emoji: str | None = None,
    description: str | None = None, parent_id: UUID | None = None,
    is_public: bool = False,
) -> Collection:
    """Create a new collection."""
    collection = Collection(
        owner_id=user_id,
        name=name,
        emoji=emoji,
        description=description,
        parent_id=parent_id,
        is_public=is_public,
    )
    db.add(collection)
    await db.flush()
    return collection


async def list_collections(
    db: AsyncSession, user_id: UUID, parent_id: UUID | None = None
) -> list[Collection]:
    """List user's collections, optionally filtered by parent."""
    query = (
        select(Collection)
        .options(selectinload(Collection.children))
        .where(
            and_(
                Collection.owner_id == user_id,
                Collection.parent_id == parent_id,
            )
        )
        .order_by(Collection.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def get_collection(
    db: AsyncSession, user_id: UUID, collection_id: UUID
) -> Collection | None:
    """Get a collection by ID, ensuring ownership."""
    result = await db.execute(
        select(Collection)
        .options(
            selectinload(Collection.children),
            selectinload(Collection.products).selectinload(Product.images),
        )
        .where(
            and_(
                Collection.id == collection_id,
                Collection.owner_id == user_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def add_product_to_collection(
    db: AsyncSession, user_id: UUID, collection_id: UUID, product_id: UUID
) -> bool:
    """Add a product to a collection (verifying ownership of both)."""
    collection = await get_collection(db, user_id, collection_id)
    product = await get_product(db, user_id, product_id)
    if not collection or not product:
        return False

    # Check if already in collection
    existing = await db.execute(
        select(ProductCollection).where(
            and_(
                ProductCollection.product_id == product_id,
                ProductCollection.collection_id == collection_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        return True  # already added

    db.add(ProductCollection(product_id=product_id, collection_id=collection_id))
    await db.flush()
    return True


# ── Helpers ──────────────────────────────────────────────────────────────

async def _sync_tags(db: AsyncSession, product: Product, tag_names: list[str]) -> None:
    """Sync a product's tags — create any new ones, link them."""
    # Clear existing tags
    await db.execute(
        ProductTag.__table__.delete().where(ProductTag.product_id == product.id)
    )

    for name in tag_names:
        name = name.strip().lower()
        if not name:
            continue
        # Get or create tag
        result = await db.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            await db.flush()
        db.add(ProductTag(product_id=product.id, tag_id=tag.id))


async def _download_and_store_images(
    db: AsyncSession, product: Product, image_urls: list[str]
) -> None:
    """Download images from URLs and upload to S3."""
    for i, url in enumerate(image_urls):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/jpeg")
                if "image" not in content_type:
                    continue
                s3_key = upload_image(resp.content, content_type)
                db.add(ProductImage(
                    product_id=product.id,
                    s3_key=s3_key,
                    position=i,
                ))
        except Exception as e:
            logger.warning("image_download_failed", url=url, error=str(e))
            # Fallback: store the direct external URL as s3_key so it is still renderable
            db.add(ProductImage(
                product_id=product.id,
                s3_key=url,
                position=i,
            ))
