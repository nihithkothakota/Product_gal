"""
Seed the category taxonomy from the PRD's defined categories.
Run: python -m app.seeds.categories
"""

import asyncio
import uuid

from sqlalchemy import select

from app.core.database import async_session_factory, engine, Base
from app.models.category import Category

# ── Category taxonomy from the PRD ───────────────────────────────────────
CATEGORIES = [
    {
        "name": "Electronics", "slug": "electronics", "icon": "📱", "sort_order": 1,
        "children": [
            {"name": "Phones", "slug": "electronics-phones", "icon": "📱"},
            {"name": "Tablets", "slug": "electronics-tablets", "icon": "📲"},
            {"name": "Laptops", "slug": "electronics-laptops", "icon": "💻"},
            {"name": "Accessories", "slug": "electronics-accessories", "icon": "🎧"},
            {"name": "Cameras", "slug": "electronics-cameras", "icon": "📷"},
            {"name": "Wearables", "slug": "electronics-wearables", "icon": "⌚"},
            {"name": "Audio", "slug": "electronics-audio", "icon": "🔊"},
            {"name": "Gaming", "slug": "electronics-gaming", "icon": "🎮"},
        ],
    },
    {
        "name": "Fashion", "slug": "fashion", "icon": "👗", "sort_order": 2,
        "children": [
            {"name": "Clothing", "slug": "fashion-clothing", "icon": "👕"},
            {"name": "Shoes", "slug": "fashion-shoes", "icon": "👟"},
            {"name": "Bags", "slug": "fashion-bags", "icon": "👜"},
            {"name": "Watches", "slug": "fashion-watches", "icon": "⌚"},
            {"name": "Jewelry", "slug": "fashion-jewelry", "icon": "💍"},
            {"name": "Sunglasses", "slug": "fashion-sunglasses", "icon": "🕶️"},
        ],
    },
    {
        "name": "Books", "slug": "books", "icon": "📚", "sort_order": 3,
        "children": [
            {"name": "Fiction", "slug": "books-fiction", "icon": "📖"},
            {"name": "Non-Fiction", "slug": "books-nonfiction", "icon": "📘"},
            {"name": "Textbooks", "slug": "books-textbooks", "icon": "📕"},
            {"name": "Comics & Manga", "slug": "books-comics", "icon": "🗯️"},
        ],
    },
    {
        "name": "Furniture", "slug": "furniture", "icon": "🪑", "sort_order": 4,
        "children": [
            {"name": "Living Room", "slug": "furniture-living", "icon": "🛋️"},
            {"name": "Bedroom", "slug": "furniture-bedroom", "icon": "🛏️"},
            {"name": "Office", "slug": "furniture-office", "icon": "🪑"},
            {"name": "Outdoor", "slug": "furniture-outdoor", "icon": "🏡"},
        ],
    },
    {
        "name": "Home", "slug": "home", "icon": "🏠", "sort_order": 5,
        "children": [
            {"name": "Kitchen", "slug": "home-kitchen", "icon": "🍳"},
            {"name": "Decor", "slug": "home-decor", "icon": "🖼️"},
            {"name": "Lighting", "slug": "home-lighting", "icon": "💡"},
            {"name": "Storage", "slug": "home-storage", "icon": "📦"},
            {"name": "Appliances", "slug": "home-appliances", "icon": "🧹"},
        ],
    },
    {
        "name": "Beauty", "slug": "beauty", "icon": "💄", "sort_order": 6,
        "children": [
            {"name": "Skincare", "slug": "beauty-skincare", "icon": "🧴"},
            {"name": "Makeup", "slug": "beauty-makeup", "icon": "💄"},
            {"name": "Haircare", "slug": "beauty-haircare", "icon": "💇"},
            {"name": "Fragrances", "slug": "beauty-fragrances", "icon": "🌸"},
        ],
    },
    {
        "name": "Sports", "slug": "sports", "icon": "⚽", "sort_order": 7,
        "children": [
            {"name": "Fitness", "slug": "sports-fitness", "icon": "🏋️"},
            {"name": "Outdoor Sports", "slug": "sports-outdoor", "icon": "🚴"},
            {"name": "Sportswear", "slug": "sports-wear", "icon": "👟"},
            {"name": "Equipment", "slug": "sports-equipment", "icon": "🏸"},
        ],
    },
    {
        "name": "Travel", "slug": "travel", "icon": "✈️", "sort_order": 8,
        "children": [
            {"name": "Luggage", "slug": "travel-luggage", "icon": "🧳"},
            {"name": "Travel Gear", "slug": "travel-gear", "icon": "🎒"},
            {"name": "Travel Accessories", "slug": "travel-accessories", "icon": "🗺️"},
        ],
    },
    {
        "name": "Automotive", "slug": "automotive", "icon": "🚗", "sort_order": 9,
        "children": [
            {"name": "Car Accessories", "slug": "auto-accessories", "icon": "🔧"},
            {"name": "Bike Accessories", "slug": "auto-bike", "icon": "🏍️"},
            {"name": "EV & Charging", "slug": "auto-ev", "icon": "⚡"},
        ],
    },
    {
        "name": "Food", "slug": "food", "icon": "🍕", "sort_order": 10,
        "children": [
            {"name": "Snacks", "slug": "food-snacks", "icon": "🍿"},
            {"name": "Beverages", "slug": "food-beverages", "icon": "🧃"},
            {"name": "Gourmet", "slug": "food-gourmet", "icon": "🧀"},
            {"name": "Health Foods", "slug": "food-health", "icon": "🥗"},
        ],
    },
]


async def seed_categories():
    """Insert the category taxonomy into the database."""
    async with async_session_factory() as session:
        # Check if categories already exist
        result = await session.execute(select(Category).limit(1))
        if result.scalar_one_or_none():
            print("Categories already seeded, skipping.")
            return

        for cat_data in CATEGORIES:
            children_data = cat_data.pop("children", [])
            parent = Category(**cat_data)
            session.add(parent)
            await session.flush()

            for i, child_data in enumerate(children_data):
                child = Category(
                    **child_data,
                    parent_id=parent.id,
                    sort_order=i + 1,
                )
                session.add(child)

        await session.commit()
        print(f"✅ Seeded {len(CATEGORIES)} top-level categories with sub-categories.")


if __name__ == "__main__":
    asyncio.run(seed_categories())
