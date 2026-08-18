"""
Search endpoint — keyword + filtered search.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.storage import generate_presigned_url
from app.models.user import User
from app.schemas.search import SearchQuery, SearchResponse
from app.services.search import search_products

router = APIRouter(prefix="/search", tags=["Search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Search products",
)
async def search(
    q: str = "",
    category: str | None = None,
    price_min: float | None = Query(None, ge=0),
    price_max: float | None = Query(None, ge=0),
    store: str | None = None,
    source: str | None = None,
    tag: str | None = None,
    is_purchased: bool | None = None,
    is_favorite: bool | None = None,
    sort_by: str = Query("saved_at", regex="^(saved_at|price_current|title|relevance)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search saved products with keyword + filters.

    Supports:
    - Full-text keyword search (title, description, brand, store, notes)
    - Filters: category, price range, store, source, tags, purchase/favorite status
    - Sorting: saved_at, price, title, relevance (when searching)
    - Pagination
    """
    query = SearchQuery(
        q=q,
        category=category,
        price_min=price_min,
        price_max=price_max,
        store=store,
        source=source,
        tag=tag,
        is_purchased=is_purchased,
        is_favorite=is_favorite,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    products, total = await search_products(db, current_user.id, query)

    items = []
    for p in products:
        images = []
        for img in (p.images or []):
            try:
                if img.s3_key.startswith(("http://", "https://", "/v1/static/")):
                    url = img.s3_key
                else:
                    url = generate_presigned_url(img.s3_key)
            except Exception:
                url = ""
            images.append({"id": str(img.id), "url": url, "position": img.position})

        items.append({
            "id": str(p.id),
            "title": p.title,
            "brand": p.brand,
            "price_current": float(p.price_current) if p.price_current else None,
            "currency": p.currency,
            "store": p.store,
            "source": p.source,
            "status": p.status.value,
            "is_favorite": p.is_favorite,
            "is_purchased": p.is_purchased,
            "tags": [t.name for t in (p.tags or [])],
            "images": images,
            "saved_at": p.saved_at.isoformat(),
        })

    return SearchResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size < total),
        query=q,
    )
