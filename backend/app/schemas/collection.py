"""
Pydantic schemas for collection CRUD operations.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    emoji: str | None = Field(None, max_length=10)
    description: str | None = None
    parent_id: UUID | None = None
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    emoji: str | None = None
    description: str | None = None
    is_public: bool | None = None
    parent_id: UUID | None = None


from app.schemas.product import ProductResponse


class CollectionResponse(BaseModel):
    id: str
    name: str
    emoji: str | None
    description: str | None
    is_public: bool
    share_code: str | None
    parent_id: str | None
    product_count: int = 0
    children: list["CollectionResponse"] = []
    products: list[ProductResponse] = []
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class CollectionListResponse(BaseModel):
    items: list[CollectionResponse]
    total: int


class AddProductToCollection(BaseModel):
    product_id: UUID
