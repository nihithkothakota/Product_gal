"""
Category model — hierarchical product taxonomy using ltree-style
adjacency list with parent_id for unlimited nesting.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)  # emoji icon
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Adjacency list for nesting
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    children = relationship("Category", back_populates="parent", lazy="selectin")
    parent = relationship("Category", back_populates="children", remote_side=[id])

    def __repr__(self) -> str:
        return f"<Category {self.icon or ''} {self.name}>"
