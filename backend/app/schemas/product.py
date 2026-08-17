"""
Pydantic schemas for product CRUD operations.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ProductCreate(BaseModel):
    """Create a product via URL or manual entry."""
    source_url: str | None = None
    title: str | None = Field(None, max_length=500)
    description: str | None = None
    brand: str | None = Field(None, max_length=255)
    category_id: UUID | None = None
    price_current: float | None = Field(None, ge=0)
    currency: str = "INR"
    store: str | None = Field(None, max_length=255)
    source: str | None = Field(None, max_length=100)
    notes: str | None = None
    tags: list[str] = []
    collection_ids: list[UUID] = []
    image_url: str | None = None
    priority: int = Field(0, ge=0, le=5)


class ProductUpdate(BaseModel):
    """Partial update of a product."""
    title: str | None = None
    description: str | None = None
    brand: str | None = None
    category_id: UUID | None = None
    price_current: float | None = None
    currency: str | None = None
    store: str | None = None
    notes: str | None = None
    priority: int | None = None
    is_favorite: bool | None = None
    is_purchased: bool | None = None
    tags: list[str] | None = None
    collection_ids: list[UUID] | None = None


class ProductImageResponse(BaseModel):
    id: str
    url: str  # presigned URL
    position: int

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    id: str
    title: str | None
    description: str | None
    brand: str | None
    category_id: str | None
    category_name: str | None = None
    price_current: float | None
    currency: str
    store: str | None
    source: str | None
    source_url: str | None
    status: str
    priority: int
    rating: float | None
    notes: str | None
    is_favorite: bool
    is_purchased: bool
    tags: list[str] = []
    collections: list[dict] = []
    images: list[ProductImageResponse] = []
    saved_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class ProductBulkAction(BaseModel):
    """Bulk operations on multiple products."""
    product_ids: list[UUID]
    action: str  # delete | favorite | unfavorite | purchased | move_to_collection
    collection_id: UUID | None = None


class ProductExtractRequest(BaseModel):
    url: str


class ProductExtractResponse(BaseModel):
    title: str | None = None
    description: str | None = None
    brand: str | None = None
    price: float | None = None
    currency: str | None = None
    store: str | None = None
    source: str | None = None
    image_urls: list[str] = []
