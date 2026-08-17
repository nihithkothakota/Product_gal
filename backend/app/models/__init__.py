"""
ORM models package. Imports all models so Alembic can discover them.
"""

from app.models.user import User  # noqa: F401
from app.models.product import Product, ProductStatus  # noqa: F401
from app.models.collection import Collection, ProductCollection, CollectionMember  # noqa: F401
from app.models.tag import Tag, ProductTag  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.image import ProductImage  # noqa: F401
from app.models.price_history import PriceHistory  # noqa: F401
from app.models.notification import Notification  # noqa: F401
