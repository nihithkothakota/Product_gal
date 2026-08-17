"""
Pydantic schemas for search queries and results.
"""

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    q: str = Field("", description="Search query text")
    category: str | None = None
    price_min: float | None = Field(None, ge=0)
    price_max: float | None = Field(None, ge=0)
    store: str | None = None
    source: str | None = None
    tag: str | None = None
    is_purchased: bool | None = None
    is_favorite: bool | None = None
    sort_by: str = "saved_at"  # saved_at | price | title
    sort_order: str = "desc"  # asc | desc
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class SearchResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int
    has_next: bool
    query: str
