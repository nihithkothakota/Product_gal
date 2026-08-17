"""
Search service — PostgreSQL full-text search with filters.
Phase 1 uses tsvector + GIN indexes directly in Postgres.
Phase 3 will migrate keyword search to OpenSearch while keeping
pgvector for semantic queries.
"""

from uuid import UUID

import structlog
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.schemas.search import SearchQuery

logger = structlog.get_logger()


async def search_products(
    db: AsyncSession,
    user_id: UUID,
    query: SearchQuery,
) -> tuple[list[Product], int]:
    """
    Full-text + filtered search using PostgreSQL.

    Supports:
    - Keyword search via to_tsvector/to_tsquery (with ranking)
    - Filters: category, price range, store, source, tags, favorite, purchased
    - Sorting: saved_at, price, title, relevance (when searching)
    - Cursor-less pagination (offset/limit for Phase 1)
    """

    base_query = (
        select(Product)
        .options(
            selectinload(Product.images),
            selectinload(Product.tags),
        )
        .where(
            and_(
                Product.user_id == user_id,
                Product.is_deleted == False,
            )
        )
    )

    # ── Full-text search ─────────────────────────────────────────────────
    if query.q and query.q.strip():
        search_term = query.q.strip()
        # Use PostgreSQL full-text search
        ts_query = func.plainto_tsquery("english", search_term)
        ts_vector = func.to_tsvector(
            "english",
            func.coalesce(Product.title, "")
            + " "
            + func.coalesce(Product.description, "")
            + " "
            + func.coalesce(Product.brand, "")
            + " "
            + func.coalesce(Product.store, "")
            + " "
            + func.coalesce(Product.notes, ""),
        )

        base_query = base_query.where(ts_vector.op("@@")(ts_query))

        # Add relevance ranking if sorting by relevance
        if query.sort_by == "relevance":
            rank = func.ts_rank(ts_vector, ts_query)
            base_query = base_query.order_by(rank.desc())

    # ── Filters ──────────────────────────────────────────────────────────
    if query.category:
        base_query = base_query.where(
            Product.category_id == query.category
        )

    if query.price_min is not None:
        base_query = base_query.where(Product.price_current >= query.price_min)

    if query.price_max is not None:
        base_query = base_query.where(Product.price_current <= query.price_max)

    if query.store:
        base_query = base_query.where(
            func.lower(Product.store) == query.store.lower()
        )

    if query.source:
        base_query = base_query.where(
            func.lower(Product.source) == query.source.lower()
        )

    if query.is_purchased is not None:
        base_query = base_query.where(Product.is_purchased == query.is_purchased)

    if query.is_favorite is not None:
        base_query = base_query.where(Product.is_favorite == query.is_favorite)

    if query.tag:
        base_query = base_query.where(
            Product.tags.any(name=query.tag.lower())
        )

    # ── Count ────────────────────────────────────────────────────────────
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # ── Sort (if not already sorted by relevance) ────────────────────────
    if query.sort_by != "relevance" or not query.q:
        sort_column = getattr(Product, query.sort_by, Product.saved_at)
        if query.sort_order == "desc":
            base_query = base_query.order_by(sort_column.desc())
        else:
            base_query = base_query.order_by(sort_column.asc())

    # ── Paginate ─────────────────────────────────────────────────────────
    offset = (query.page - 1) * query.page_size
    base_query = base_query.offset(offset).limit(query.page_size)

    result = await db.execute(base_query)
    products = list(result.scalars().unique().all())

    logger.info(
        "search_executed",
        query=query.q,
        total=total,
        returned=len(products),
    )

    return products, total
