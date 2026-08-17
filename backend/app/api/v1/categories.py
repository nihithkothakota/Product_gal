"""
Category endpoints — read-only taxonomy tree.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryResponse, CategoryTreeResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


def _category_to_response(cat: Category) -> CategoryResponse:
    return CategoryResponse(
        id=str(cat.id),
        name=cat.name,
        slug=cat.slug,
        icon=cat.icon,
        description=cat.description,
        sort_order=cat.sort_order,
        parent_id=str(cat.parent_id) if cat.parent_id else None,
        children=[_category_to_response(c) for c in (cat.children or [])] if not cat.parent_id else [],
    )


@router.get(
    "",
    response_model=CategoryTreeResponse,
    summary="Get category tree",
)
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Return the full category taxonomy as a nested tree."""
    result = await db.execute(
        select(Category)
        .options(selectinload(Category.children))
        .where(Category.parent_id == None)  # noqa: E711 — SQLAlchemy requires == None
        .order_by(Category.sort_order)
    )
    root_categories = result.scalars().unique().all()

    return CategoryTreeResponse(
        categories=[_category_to_response(c) for c in root_categories]
    )
