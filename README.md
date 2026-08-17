# Product Gallery

> 🛍️ See it. Save it. Find it. Buy it.

The world's best personal product memory app — save products from anywhere on the internet, organize them effortlessly with AI, and rediscover them instantly.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)
- Flutter 3.x (for mobile app)

### 1. Start infrastructure

```bash
# Start PostgreSQL, Redis, and MinIO
docker compose up -d postgres redis minio

# Or start everything including the backend
docker compose up -d
```

### 2. Run backend locally (development)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp ../.env.example .env

# Run database migrations
alembic upgrade head

# Seed categories
python -m app.seeds

# Start the development server
uvicorn app.main:app --reload --port 8000
```

### 3. Access the API

- **Swagger Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/v1/auth/register` | POST | Create an account |
| `/v1/auth/login` | POST | Log in, get JWT tokens |
| `/v1/auth/refresh` | POST | Refresh access token |
| `/v1/auth/me` | GET | Get current user profile |
| `/v1/products` | POST | Save a new product |
| `/v1/products` | GET | List saved products |
| `/v1/products/{id}` | GET | Get product details |
| `/v1/products/{id}` | PUT | Update a product |
| `/v1/products/{id}` | DELETE | Delete a product |
| `/v1/products/{id}/favorite` | POST | Toggle favorite |
| `/v1/products/{id}/purchased` | POST | Toggle purchased |
| `/v1/collections` | POST | Create a collection |
| `/v1/collections` | GET | List collections |
| `/v1/collections/{id}` | GET/PUT/DELETE | Collection CRUD |
| `/v1/collections/{id}/products` | POST | Add product to collection |
| `/v1/categories` | GET | Get category tree |
| `/v1/search` | GET | Search products |

## Architecture

```
backend/
├── app/
│   ├── api/v1/          # Route handlers
│   ├── core/            # Config, security, database, middleware
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic
│   ├── workers/         # Async workers (Phase 2)
│   └── main.py          # FastAPI entry point
├── alembic/             # Database migrations
└── tests/               # Test suite
```

## Roadmap

- [x] **Phase 1**: Core CRUD, search, collections
- [ ] **Phase 2**: AI extraction, OCR, semantic search
- [ ] **Phase 3**: Price tracking, social, browser extension
- [ ] **Phase 4**: AI copilot, recommendations, analytics

## License

Private — All rights reserved.
