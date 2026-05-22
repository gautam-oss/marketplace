# Marketplace

**Last updated: 2026-05-22**

A full-stack e-commerce marketplace built for learning modern web development practices. Buyers browse and purchase products. Sellers list and manage inventory. Admins moderate the platform.

This repository is intentionally straightforward — every decision is practical, every pattern is something you will encounter in real production codebases.

---

## Table of Contents

- [What You Will Learn](#what-you-will-learn)
- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Key Patterns and Concepts](#key-patterns-and-concepts)
- [API Reference](#api-reference)
- [Payment Flow](#payment-flow)
- [Email and Background Tasks](#email-and-background-tasks)
- [Testing Guide](#testing-guide)
- [Common Development Tasks](#common-development-tasks)
- [Environment Variables](#environment-variables)

---

## What You Will Learn

Working through this codebase will give you hands-on experience with:

- Building a **fully async REST API** with FastAPI and SQLAlchemy 2.x
- **Role-based access control** (buyer / seller / admin) using dependency injection
- **JWT authentication** with access tokens and refresh tokens
- **Database design** — relational models, foreign keys, indexes, migrations with Alembic
- **Caching** with Redis to avoid hitting the database on every request
- **Full-text search** with Elasticsearch
- **File uploads** to AWS S3
- **Payment processing** with Razorpay (webhook verification, idempotency)
- **Background tasks** with Celery (email sending, image processing)
- **Writing tests** with pytest-asyncio and a real test database
- **CI/CD** with GitHub Actions

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI (Python 3.12) | Modern, fast, automatic OpenAPI docs, async-first |
| ORM | SQLAlchemy 2.x async | Type-safe DB access, works with Alembic for migrations |
| Database | PostgreSQL 16 | Industry-standard relational DB |
| Cache | Redis 7 | Sub-millisecond reads, used for caching and rate limiting |
| Search | Elasticsearch 8 | Full-text search with filters and ranking |
| Frontend | React 18 + Vite + TypeScript | Component-based UI, type safety, fast dev server |
| State | Zustand + React Query | Global state (auth/cart) + server state (API data) |
| Auth | JWT (python-jose + passlib) | Stateless, scalable authentication |
| Background | Celery + Redis broker | Offload slow work (emails, image resizing) from the request cycle |
| Payments | Razorpay | India-first payment gateway — UPI, cards, net banking |
| Email | Resend SDK | Transactional email via API (no SMTP configuration) |
| Storage | AWS S3 | Scalable object storage for product images |
| Monitoring | Sentry | Error tracking in production |
| CI/CD | GitHub Actions | Automated tests and lint on every push |

---

## Architecture Overview

```
Browser (React + Vite)
        |
        | HTTP/JSON
        v
FastAPI (backend/app/main.py)
   |          |            |
   v          v            v
PostgreSQL   Redis      Elasticsearch
(SQLAlchemy) (cache,     (full-text
             rate limit)  search)
   |
   v
Celery Worker (background tasks)
   |          |
   v          v
Resend API  AWS S3
(email)     (images)
```

**Request lifecycle for a typical API call:**

1. Browser sends `GET /api/v1/products`
2. FastAPI router receives the request
3. Dependency injection resolves `get_db` (database session) automatically
4. Route handler checks Redis cache — returns immediately if cached
5. On cache miss, CRUD layer queries PostgreSQL
6. Result is serialized via a Pydantic schema and written to Redis cache
7. JSON response sent to browser

**Authentication flow:**

1. `POST /api/v1/auth/login` → returns `access_token` (30 min) and `refresh_token` (7 days)
2. Client stores tokens, sends `Authorization: Bearer <access_token>` on every request
3. `get_current_user` dependency decodes and validates the token
4. `require_role("seller")` dependency additionally checks the user's role
5. When the access token expires, client calls `POST /api/v1/auth/refresh` to get a new one

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL2 backend (Windows) or standard (Mac/Linux)
- [Node.js 20+](https://nodejs.org/)
- [Python 3.12+](https://www.python.org/)
- Git

### 1. Clone and configure

```bash
git clone <repo-url>
cd marketplace
cp .env.example .env
```

Open `.env` and fill in your credentials. For local development, the database and Redis values are pre-filled — you only need to add Razorpay, Resend, and AWS keys if you want to test payments, email, or image uploads. Set `USE_LOCAL_STORAGE=true` to skip S3 and save images locally.

### 2. Start infrastructure

```bash
docker compose up -d postgres redis elasticsearch
```

This starts PostgreSQL, Redis, and Elasticsearch as background containers. Check they are healthy:

```bash
docker compose ps
```

All three should show `(healthy)`.

### 3. Set up the backend

```bash
cd backend
python -m venv .venv

# Activate the virtual environment:
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows Git Bash / Mac / Linux:
source .venv/Scripts/activate   # Windows Git Bash
source .venv/bin/activate        # Mac / Linux

pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now running at **http://localhost:8000**. Interactive docs: **http://localhost:8000/docs**

### 4. Set up the frontend

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The app is now running at **http://localhost:5173**

### 5. Seed the database

Open a third terminal with the backend venv active:

```bash
cd backend
python seed.py
```

This creates sample users, categories, products, orders, and reviews.

**Seed accounts** (all passwords: `Test1234!`):

| Email | Role | Notes |
|---|---|---|
| `admin@marketplace.dev` | admin | Full platform access |
| `ravi@seller.dev` | seller | Electronics products |
| `priya@seller.dev` | seller | Fashion and home products |
| `amit@buyer.dev` | buyer | Has two past orders |
| `sneha@buyer.dev` | buyer | Has one active order |
| `rohan@buyer.dev` | buyer | No orders yet |

---

## Project Structure

```
marketplace/
├── backend/
│   ├── app/
│   │   ├── main.py           # App entry point, router registration, lifespan events
│   │   ├── core/
│   │   │   ├── config.py     # All settings loaded from environment variables
│   │   │   ├── database.py   # Async SQLAlchemy engine and session factory
│   │   │   ├── security.py   # Password hashing, JWT creation and decoding
│   │   │   ├── redis.py      # Redis client, cache helpers (get/set/delete)
│   │   │   └── deps.py       # FastAPI dependencies: get_db, get_current_user, require_role
│   │   ├── api/v1/
│   │   │   ├── auth.py       # Register, login, refresh, logout, /me
│   │   │   ├── products.py   # CRUD + image upload + search + caching
│   │   │   ├── categories.py # Category tree management
│   │   │   ├── cart.py       # Redis-backed shopping cart
│   │   │   ├── orders.py     # Checkout, webhook, order status transitions
│   │   │   ├── reviews.py    # Product reviews with one-review-per-buyer enforcement
│   │   │   ├── users.py      # User profile and seller management
│   │   │   └── admin.py      # Platform stats, user management, order oversight
│   │   ├── models/           # SQLAlchemy ORM models (one file per domain)
│   │   ├── schemas/          # Pydantic v2 request/response shapes
│   │   ├── crud/             # Database query functions (no business logic here)
│   │   ├── services/         # External integrations (S3, Elasticsearch, Razorpay, cart)
│   │   └── tasks/            # Celery background tasks (email, image processing)
│   ├── alembic/              # Database migration files
│   ├── seed.py               # Development data seeder
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/              # Axios client and per-domain API functions
│       ├── components/       # Reusable UI components
│       ├── pages/            # Route-level page components
│       ├── hooks/            # React Query hooks for data fetching
│       ├── store/            # Zustand stores (auth, cart)
│       └── types/            # TypeScript interfaces mirroring backend schemas
├── tests/
│   ├── conftest.py           # Test fixtures: database, HTTP client, user tokens
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
│   ├── test_cart.py
│   ├── test_categories.py
│   └── test_order_status.py
├── .github/workflows/ci.yml  # GitHub Actions CI pipeline
├── docker-compose.yml        # Local development services
└── pyproject.toml            # Ruff linter configuration
```

### How the layers connect

A request to `GET /api/v1/products` flows through:

```
api/v1/products.py   →   crud/product.py   →   models/product.py
(route handler)          (DB query)             (ORM definition)
       |                                               |
schemas/product.py                           core/database.py
(serialize response)                         (session/engine)
```

- **models/** defines the database table structure using SQLAlchemy ORM
- **crud/** contains pure async functions that query the database — no HTTP concepts here
- **schemas/** defines what data comes in (request body) and goes out (response) using Pydantic
- **api/v1/** ties everything together: validates input via schemas, calls crud functions, returns responses

---

## Key Patterns and Concepts

### Dependency Injection

FastAPI's `Depends()` system is used throughout. Instead of each route creating its own database session or decoding JWT tokens manually, these are declared as dependencies:

```python
@router.get("/products/{slug}", response_model=ProductResponse)
async def get_product(
    slug: str,
    db: AsyncSession = Depends(get_db),           # DB session injected automatically
    current_user = Depends(get_current_active_user),  # Parsed JWT, user loaded from DB
):
    ...
```

`require_role("seller")` is a dependency factory — it returns a dependency that checks the user's role:

```python
@router.post("/products")
async def create_product(
    current_user = Depends(require_role("seller", "admin")),  # 403 if buyer calls this
):
    ...
```

### Async Database Access

Every database operation uses `async/await`. Never use synchronous SQLAlchemy calls in this codebase — they will block the event loop and kill performance.

```python
# Correct
result = await db.execute(select(Product).where(Product.slug == slug))
product = result.scalar_one_or_none()

# Wrong — never do this
product = db.query(Product).filter(Product.slug == slug).first()
```

### Pydantic Schemas vs ORM Models

The ORM model (`models/product.py`) represents the database table. The Pydantic schema (`schemas/product.py`) represents what the API accepts or returns. They are deliberately separate:

- Input schemas validate and sanitize incoming data
- Response schemas control exactly what fields are exposed — you never accidentally leak a password hash
- `model_validate(orm_object)` converts an ORM object to a Pydantic schema

### Redis Caching

Frequently read data (product listings, individual product pages) is cached in Redis. The cache key encodes the query parameters so different filters get different cache entries:

```python
cached = await cache_get(cache_key)
if cached:
    return json.loads(cached)           # Fast path — no DB query
# ... DB query ...
await cache_set(cache_key, result.model_dump_json(), ttl=120)  # Cache for 2 minutes
```

When a product is updated or deleted, its cache entries are explicitly invalidated.

### SELECT FOR UPDATE (Preventing Race Conditions)

During checkout, stock is decremented using `SELECT FOR UPDATE` to prevent two buyers from purchasing the last item simultaneously:

```python
result = await db.execute(
    select(Product).where(Product.id == product_id).with_for_update()
)
locked_product = result.scalar_one_or_none()
locked_product.stock -= quantity  # Safe — row is locked until transaction commits
```

### Alembic Migrations

Never modify database tables by hand. Instead:

```bash
# After changing a model, generate a migration automatically
alembic revision --autogenerate -m "add phone number to users"

# Review the generated file in alembic/versions/, then apply it
alembic upgrade head

# Roll back one step if something went wrong
alembic downgrade -1
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive docs (Swagger UI): `http://localhost:8000/docs`

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create buyer account |
| POST | `/auth/login` | None | Get access + refresh tokens |
| POST | `/auth/refresh` | None | Exchange refresh token for new access token |
| POST | `/auth/logout` | Bearer | Logout (client should discard tokens) |
| GET | `/auth/me` | Bearer | Get current user profile |
| PATCH | `/auth/me` | Bearer | Update name / avatar |

### Products

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/products` | None | List active products (filterable, paginated) |
| GET | `/products/{slug}` | None | Product detail with reviews |
| POST | `/products` | seller / admin | Create product with images (multipart form) |
| PUT | `/products/{id}` | seller (own) / admin | Update product details |
| PATCH | `/products/{id}/status` | seller (own) / admin | Change status: draft / active / archived |
| DELETE | `/products/{id}` | seller (own) / admin | Soft-delete product |

**Filtering and sorting** (`GET /products`):

```
?q=wireless+earbuds          # Full-text search via Elasticsearch
?category=smartphones        # Filter by category slug
?min_price=500&max_price=5000
?sort=price_asc              # newest | price_asc | price_desc | rating
?page=2&per_page=20
```

### Cart

Cart is stored in Redis, not the database. It is tied to the user's ID.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/cart` | Bearer | Get current cart with product details |
| POST | `/cart/items` | Bearer | Add item or increase quantity |
| PUT | `/cart/items/{product_id}` | Bearer | Set exact quantity |
| DELETE | `/cart/items/{product_id}` | Bearer | Remove item |
| DELETE | `/cart` | Bearer | Clear entire cart |

### Orders

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/orders/checkout` | buyer | Create order + Razorpay order from cart |
| POST | `/orders/webhook` | None | Razorpay payment webhook (signature verified) |
| GET | `/orders` | buyer / seller | List own orders |
| GET | `/orders/{id}` | buyer (own) / admin | Order detail |
| PATCH | `/orders/{id}/status` | seller / admin | Advance order status |
| POST | `/orders/{id}/cancel` | buyer (own) | Cancel pending order |

### Reviews

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/products/{slug}/reviews` | None | List reviews for a product |
| POST | `/products/{slug}/reviews` | buyer | Create review (one per buyer per product) |
| PATCH | `/reviews/{id}` | owner | Edit your review |
| DELETE | `/reviews/{id}` | owner / admin | Delete review |

### Admin

All admin routes require the `admin` role.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/stats` | Platform statistics (users, orders, revenue) |
| GET | `/admin/users` | List all users |
| PATCH | `/admin/users/{id}/deactivate` | Deactivate a user account |
| PATCH | `/admin/users/{id}/activate` | Reactivate a user account |
| GET | `/admin/orders` | List all orders with filters |
| PATCH | `/admin/orders/{id}/status` | Override any order status |

### Pagination

All list endpoints return:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

---

## Payment Flow

This project uses **Razorpay** — the standard Indian payment gateway supporting UPI, cards, net banking, and wallets.

```
1. Buyer adds items to cart
         |
         v
2. POST /orders/checkout
   → Validate stock (SELECT FOR UPDATE)
   → Calculate total: subtotal + 18% GST + ₹50 shipping (free over ₹500)
   → razorpay_client.orders.create(amount in paise, currency="INR")
   → Save Order (status=pending) with razorpay_order_id
   → Return { razorpay_order_id, amount_paise, razorpay_key_id }
         |
         v
3. Frontend opens Razorpay checkout modal
   → new window.Razorpay({ key, amount, order_id, handler })
   → rzp.open()
         |
         v
4. Buyer completes payment (UPI / card / etc.)
         |
         v
5. Razorpay POSTs to POST /orders/webhook
   → Verify X-Razorpay-Signature header (HMAC-SHA256)
   → payment.captured → mark order paid → send confirmation email (Celery)
   → payment.failed   → mark order cancelled → restore stock
```

**For local webhook testing**, use ngrok to expose your local server:

```bash
ngrok http 8000
# Add the generated URL to Razorpay Dashboard → Settings → Webhooks
# URL: https://xxxx.ngrok.io/api/v1/orders/webhook
# Events: payment.captured, payment.failed
```

---

## Email and Background Tasks

Emails are sent via **Resend** (not SMTP). Order confirmation, shipping notification, and delivery confirmation emails are triggered as **Celery background tasks** so the API response is not delayed by email sending.

```python
# In the webhook handler — fire and forget
send_order_confirmation_email.delay(str(order.id), user.email, user.full_name)
```

The Celery worker picks this up from the Redis queue and calls the Resend API:

```python
import resend
resend.Emails.send({
    "from": settings.EMAIL_FROM,
    "to": [user_email],
    "subject": f"Order Confirmed! #{order_id[:8].upper()}",
    "html": html_body,
})
```

To run the Celery worker locally:

```bash
cd backend
celery -A app.tasks.celery_app worker -l info --concurrency 2
```

---

## Testing Guide

Tests use a real PostgreSQL database (`marketplace_test`) — not mocks. This catches issues that in-memory fakes would miss.

### Running tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run a single file
pytest tests/test_auth.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing
```

### How tests are structured

Each test gets a clean database — `conftest.py` truncates all tables after every test. Fixtures provide everything a test needs:

```python
async def test_create_product_as_seller(async_client, seller_token, test_db):
    # async_client  — httpx AsyncClient wired to the FastAPI app
    # seller_token  — valid JWT for a seller user
    # test_db       — AsyncSession to the test database

    response = await async_client.post(
        "/api/v1/products",
        data={"title": "Test Product", "price": "999", "stock": "10"},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Product"
```

### What to test for every route

Each route should have at least these cases:

| Test case | What it verifies |
|---|---|
| Happy path | Route works correctly with valid input |
| Unauthenticated | Returns 401 when no token is provided |
| Wrong role | Returns 403 when a buyer calls a seller-only route |
| Not found | Returns 404 for a non-existent resource |
| Conflict | Returns 409 for duplicates (e.g., email already registered) |

---

## Common Development Tasks

### Add a new API field to a model

1. Add the column to the model in `backend/app/models/`
2. Add the field to the relevant Pydantic schemas in `backend/app/schemas/`
3. Generate and apply the migration:
   ```bash
   alembic revision --autogenerate -m "add field_name to table_name"
   alembic upgrade head
   ```
4. Update the CRUD function if the field needs to be set on create/update
5. Add or update tests

### Add a new API route

1. Create or edit a file in `backend/app/api/v1/`
2. Register the router in `backend/app/main.py` (follow the existing pattern)
3. Add request/response schemas to `backend/app/schemas/`
4. Add the DB query to `backend/app/crud/`
5. Write tests in `tests/test_<resource>.py`

### Reset the development database

```bash
docker compose down -v          # Stop containers and delete volumes
docker compose up -d postgres redis elasticsearch
cd backend
alembic upgrade head
python seed.py
```

### Check and fix linting errors

```bash
cd marketplace   # project root
ruff check backend/app/         # show errors
ruff check backend/app/ --fix   # auto-fix safe errors
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Database (pre-configured for Docker)
DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200

# Auth — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<your-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Razorpay — get test keys from https://dashboard.razorpay.com/app/keys
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...

# Email — get key from https://resend.com/api-keys
RESEND_API_KEY=re_...
EMAIL_FROM=onboarding@resend.dev

# AWS S3 — or set USE_LOCAL_STORAGE=true to skip S3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-bucket-name
USE_LOCAL_STORAGE=false

# Sentry — optional, leave blank to disable
SENTRY_DSN=

# CORS — comma-separated list of allowed frontend origins
ALLOWED_ORIGINS=http://localhost:5173
```

---

## CI/CD

GitHub Actions runs on every push to `main` or `develop` and on pull requests to `main`.

| Job | What it does |
|---|---|
| `backend-test` | Spins up PostgreSQL + Redis, installs dependencies, runs all 105 pytest tests |
| `backend-lint` | Runs ruff to check for code style issues |
| `frontend-build` | TypeScript type check + Vite production build |

A green CI run means: the tests pass, the code is lint-clean, and the frontend compiles. It does not deploy anything — deployment is manual via the production Dockerfiles (`backend/Dockerfile.prod`, `frontend/Dockerfile.prod`).
