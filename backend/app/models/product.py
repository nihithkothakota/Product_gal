"""
Product model — the core entity. Includes the async-ready `status` field
and a pgvector `embedding` column for semantic search (Phase 2).
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProductStatus(str, enum.Enum):
    """Tracks the async enrichment lifecycle."""
    PROCESSING = "processing"
    ENRICHED = "enriched"
    FAILED = "failed"


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # ── Core fields ──────────────────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )

    # ── Price ────────────────────────────────────────────────────────────
    price_current: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR")

    # ── Source ───────────────────────────────────────────────────────────
    store: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Amazon, Flipkart, etc.
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # instagram, chrome, manual
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True  # SHA256 for duplicate detection
    )

    # ── Status & metadata ────────────────────────────────────────────────
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus), default=ProductStatus.PROCESSING, nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_purchased: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # soft delete

    # ── AI / Embedding (Phase 2) ─────────────────────────────────────────
    # embedding column will be added via Alembic migration with pgvector
    # embedding: Mapped[...] — deferred to Phase 2 migration

    # ── Timestamps ───────────────────────────────────────────────────────
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # ── Relationships ────────────────────────────────────────────────────
    user = relationship("User", back_populates="products")
    category = relationship("Category", lazy="joined")
    images = relationship(
        "ProductImage", back_populates="product", cascade="all, delete-orphan",
        order_by="ProductImage.position", lazy="selectin"
    )
    tags = relationship(
        "Tag", secondary="product_tags", back_populates="products", lazy="selectin"
    )
    collections = relationship(
        "Collection",
        secondary="product_collections",
        back_populates="products",
        lazy="selectin",
    )
    price_history = relationship(
        "PriceHistory", back_populates="product", cascade="all, delete-orphan",
        order_by="PriceHistory.recorded_at.desc()", lazy="noload"
    )

    # ── Indexes ──────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_products_user_id", "user_id"),
        Index("ix_products_user_status", "user_id", "status"),
        Index("ix_products_saved_at", "saved_at"),
    )

    def __repr__(self) -> str:
        return f"<Product {self.title or 'Untitled'} ({self.status.value})>"
