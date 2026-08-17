
# Product Gallery – Product Requirements Document (PRD)

## Vision
Create the world's best personal product memory app—a place where users can save products from anywhere on the internet, organize them effortlessly with AI, and rediscover them instantly.

## Target Audience
- Gen Z
- Young professionals
- Students
- Online shoppers
- Content creators
- Interior/fashion/tech enthusiasts

## Core Value Proposition
> "See it. Save it. Find it. Buy it."

Unlike WhatsApp, Telegram Saved Messages, Notes, or Bookmarks, Product Gallery is purpose-built for products.

---

# User Journey

1. User finds a product anywhere.
2. Shares it to Product Gallery.
3. AI extracts:
   - Product name
   - Brand
   - Price
   - Images
   - Category
   - Store
4. User selects or creates a collection.
5. Product becomes searchable forever.

---

# Core Features

## Universal Save
- Android/iOS Share Sheet
- Browser extension
- Copy-paste URL
- Screenshot import
- Camera import
- Manual product creation

## Sources
- Instagram
- Facebook
- Telegram
- WhatsApp
- Amazon
- Flipkart
- Myntra
- Pinterest
- YouTube
- Reddit
- Chrome
- Offline

---

# Organization

## Main Categories
- Electronics
- Fashion
- Books
- Furniture
- Home
- Beauty
- Sports
- Travel
- Automotive
- Food

## Sub Categories
Unlimited nested folders.

Example:
Electronics
 ├── Phones
 ├── Tablets
 ├── Accessories

---

# Product Card

Each product contains:

- Images
- Title
- Description
- Price
- Multiple prices
- Currency
- Store
- Source
- URL
- Rating
- Notes
- Tags
- Date saved
- Purchase status
- Favorite
- Priority
- Collections

---

# AI Features

## AI Categorization
Automatically classifies products.

## OCR
Extracts information from screenshots.

## Duplicate Detection
Detects repeated saves.

## Semantic Search
Examples:
- black sneakers under ₹5000
- books from Instagram
- gifts for mom

## AI Summary
Summarizes long product pages.

## Similar Products
Recommends alternatives.

## Price Tracking
Tracks historical price changes.

## Wishlist Intelligence
- Frequently viewed
- Forgotten items
- Best deals
- Seasonal reminders

---

# Gen Z Features

- Beautiful animations
- Glassmorphism
- Dark mode
- Emoji folders
- Collaborative collections
- Profile themes
- Shareable wishlists
- Streaks (optional)
- Monthly recap
- AI shopping assistant

---

# Social Features

- Public collections
- Friends
- Shared shopping boards
- Gift lists
- Wedding lists
- Travel packing lists

---

# Search

Filters:
- Category
- Price
- Source
- Date
- Store
- Tags
- Purchased
- Wishlist

Natural language search supported.

---

# Notifications

- Price drops
- Back in stock
- New version released
- Sale alerts
- Reminder to revisit saved items

---

# Analytics

Dashboard:
- Total saved
- Category distribution
- Money planned
- Money spent
- Top brands
- Monthly activity

---

# Monetization

Free:
- Unlimited saves
- Collections
- Search

Premium:
- AI features
- Price history
- Browser extension sync
- Unlimited shared collections
- Smart insights

---

# Suggested Tech Stack

Frontend:
- Flutter

Backend:
- FastAPI
- PostgreSQL
- Redis

AI:
- OCR
- Vision model
- LLM
- Embeddings
- pgvector

Storage:
- S3 compatible object storage

Search:
- OpenSearch

---

# Future Roadmap

Phase 1
- Save products
- Categories
- Search

Phase 2
- AI extraction
- OCR
- Semantic search

Phase 3
- Price tracking
- Shared collections
- Browser extension

Phase 4
- AI shopping copilot
- Recommendations
- Purchase insights

---

# Success Metrics

- Daily Active Users
- Products saved/day
- Search success rate
- Retention (30-day)
- Premium conversion
- Average saves per user

---

# Design Principles

- One-tap saving
- Minimal typing
- AI-first organization
- Fast (<200 ms search)
- Delightful micro-interactions
- Privacy by default
- Offline support
