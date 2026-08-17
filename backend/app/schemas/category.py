"""
Pydantic schemas for category endpoints.
"""

from pydantic import BaseModel


class CategoryResponse(BaseModel):
    id: str
    name: str
    slug: str
    icon: str | None
    description: str | None
    sort_order: int
    parent_id: str | None
    children: list["CategoryResponse"] = []

    model_config = {"from_attributes": True}


class CategoryTreeResponse(BaseModel):
    categories: list[CategoryResponse]
