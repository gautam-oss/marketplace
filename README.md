# Marketplace

**Last updated: 2026-05-23** · **v1.0** · **105 tests passing** · **CI green**

A full-stack multi-category e-commerce marketplace. Buyers browse and purchase products. Sellers list and manage inventory. Admins moderate the platform.

Every decision in this codebase is practical — the patterns, the trade-offs, and the integrations are the same ones you encounter in real production systems.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Key Patterns](#key-patterns)
- [API Reference](#api-reference)
- [Payment Flow](#payment-flow)
- [Email and Background Tasks](#email-and-background-tasks)
- [Testing](#testing)
- [Development Tasks](#development-tasks)
- [Environment Variables](#environment-variables)
- [CI/CD](#cicd)

---

## Features

**Buyer**
- Browse products with full-text search (Elasticsearch) and filters (category, price, rating, sort)
- Redis-backed cart with real-time stock validation and stale item cleanup
- Razorpay checkout — UPI, cards, net banking, wallets (India)
- Order tracking through the full lifecycle: pending → paid → processing → shipped → delivered
- Product reviews with verified purchase badge and helpful votes

**Seller**
- Product management: create, edit, archive, bulk actions
- Image upload to AWS S3 with automatic resize (max 1200×1200px, 5MB limit)
- Dashboard: revenue, active listings, recent orders, top products by sales

**Admin**
- Platform stats: users, revenue (this month vs last), orders by status
- User management: role changes, activate/deactivate (cannot change own role)
- Product moderation: approve, archive across all sellers
- Order oversight: full order list, status overrides
- Review moderation: list all reviews, filter by rating, delete any review

**Infrastructure**
- JWT auth with access + refresh tokens and login rate limiting (Redis)
- Celery background tasks for transactional emails (Resend SDK)
- Sentry error monitoring
- GitHub Actions CI: tests + lint + frontend build on every push

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | FastAPI (Python 3.12) | Async-first, automatic OpenAPI docs, fast |
| ORM | SQLAlchemy 2.x async | Type-safe queries, Alembic migrations |
| Database | PostgreSQL 16 | Industry-standard relational DB |
| Cache | Redis 7 | Sub-millisecond reads for cart, caching, rate limiting |
| Search | Elasticsearch 8 | Full-text search with filters and ranking |
| Frontend | React 18 + Vite + TypeScript | Component-based, type-safe, fast dev server |
| State | Zustand + React Query | Global state (auth/cart) + server state with caching |
| Auth | JWT (python-jose + passlib) | Stateless, role-based access control |
| Background | Celery + Redis broker | Decouple slow work (emails, image processing) |
| Payments | Razorpay | India-first — UPI, cards, net banking, wallets |
| Email | Resend SDK | Transactional email via API |
| Storage | AWS S3 ap-south-1 | Scalable object storage for product images |
| Monitoring | Sentry | Error tracking |
| CI/CD | GitHub Actions | Tests, lint, build on every push |

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Browser (React 18)            │
│  Vite · TypeScript · Tailwind · Zustand │
└────────────────┬────────────────────────┘
                 │ HTTP/JSON
                 ▼
┌─────────────────────────────────────────┐
│           FastAPI  (port 8000)          │
│     Python 3.12 · SQLAlchemy 2.x        │
└──────┬───────────┬──────────────────────┘
       │           │           │
       ▼           ▼           ▼
  PostgreSQL     Redis    Elasticsearch
  (primary DB)  (cart,    (full-text
                 cache,    search)
                 queue)
                   │
                   ▼
            Celery Worker
            /           \
        Resend          AWS S3
        (email)        (images)
```

**Typical request flow:**
1. Browser sends `GET /api/v1/products?q=laptop`
2. FastAPI resolves dependencies (DB session, JWT user) via `Depends()`
3. Route handler checks Redis cache — hits return immediately
4. Cache miss → CRUD layer queries PostgreSQL or Elasticsearch
5. Pydantic serializes response, Redis caches it (2-5 min TTL)
6. JSON returned to browser

**Checkout + payment flow:** see [Payment Flow](#payment-flow)

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL2 backend (Windows)
- [Node.js 20+](https://nodejs.org/)
- [Python 3.12+](https://www.python.org/)
- Git

### 1. Clone and configure

```bash
git clone <repo-url>
cd marketplace
cp .env.example .env
```

Open `.env` and fill in your keys. For local dev, the database values are pre-filled — you need Razorpay, Resend, and AWS keys to test payments, email, and image uploads. Set `USE_LOCAL_STORAGE=true` to skip S3.

### 2. Start infrastructure

```bash
docker compose up -d postgres redis elasticsearch
docker compose ps   # wait until all three show (healthy)
```

### 3. Set up the backend

```bash
cd backend
python -m venv .venv

# Activate:
source .venv/Scripts/activate   # Git Bash (Windows)
source .venv/bin/activate       # Mac / Linux

pip install -r requirements.txt
alembic upgrade head
python seed.py                  # load sample data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API: **http://localhost:8000** · Swagger: **http://localhost:8000/docs**

### 4. Set up the frontend

```bash
cd frontend
npm install
npm run dev
```

App: **http://localhost:5173**

### 5. (Optional) Start Celery for emails

```bash
cd backend
celery -A app.tasks.celery_app worker -l info --concurrency 2
```

### Seed accounts

All passwords: `Test1234!`

| Email | Role | Notes |
|---|---|---|
| `admin@marketplace.dev` | admin | Full platform access |
| `ravi@seller.dev` | seller | Electronics + Sports (8 products) |
| `priya@seller.dev` | seller | Fashion + Home + Books (6 products) |
| `amit@buyer.dev` | buyer | Has past orders |
| `sneha@buyer.dev` | buyer | Has past orders |
| `rohan@buyer.dev` | buyer | No orders yet |

---

## Project Structure

```
marketplace/
├── backend/
│   ├── app/
│   │   ├── main.py           # App entry, router registration, CORS, Sentry, lifespan
│   │   ├── core/
│   │   │   ├── config.py     # All settings from environment variables
│   │   │   ├── database.py   # Async engine, session factory
│   │   │   ├── security.py   # Password hashing, JWT create/decode
│   │   │   ├── redis.py      # Redis client, cache helpers
│   │   │   └── deps.py       # get_db, get_current_user, require_role factory
│   │   ├── api/v1/
│   │   │   ├── auth.py       # Register, login (rate-limited), refresh, logout, /me
│   │   │   ├── products.py   # CRUD, image upload, Elasticsearch search, Redis cache
│   │   │   ├── categories.py # Category tree (self-referential)
│   │   │   ├── cart.py       # Redis-backed cart
│   │   │   ├── orders.py     # Checkout, webhook, status transitions, cancel+refund
│   │   │   ├── reviews.py    # Product reviews + helpful votes
│   │   │   ├── users.py      # Public profiles
│   │   │   └── admin.py      # Platform management: users, products, orders, reviews, stats
│   │   ├── models/           # SQLAlchemy ORM (all imported in __init__.py for Alembic)
│   │   ├── schemas/          # Pydantic v2 request/response shapes
│   │   ├── crud/             # Async DB query functions (no HTTP concepts)
│   │   ├── services/         # External: Elasticsearch, S3, Cart (Redis), Razorpay
│   │   └── tasks/            # Celery: email tasks (Resend), image processing (Pillow)
│   ├── alembic/              # Migration files
│   ├── seed.py               # Development data seeder
│   ├── Dockerfile            # Dev image (hot reload)
│   └── Dockerfile.prod       # Production image (multi-stage, non-root, 2 workers)
├── frontend/
│   └── src/
│       ├── api/              # Axios client + per-domain API functions
│       ├── components/       # Navbar, Footer, Pagination, Toast, LoadingSpinner
│       ├── pages/
│       │   ├── (buyer)       # Home, ProductList, ProductDetail, Cart, Checkout, Orders
│       │   ├── seller/       # Dashboard, ProductList, Create/Edit Product
│       │   └── admin/        # Layout (sidebar), Dashboard, Users, Products, Orders, Reviews
│       ├── hooks/            # React Query hooks for data fetching
│       ├── store/            # Zustand: authStore, cartStore
│       └── types/            # TypeScript interfaces mirroring all backend schemas
├── tests/                    # Run from project root — 105 tests, all passing
│   ├── conftest.py           # Fixtures: async_client, test_db, buyer/seller/admin tokens
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
│   ├── test_cart.py
│   ├── test_categories.py
│   └── test_order_status.py
├── .github/workflows/ci.yml
├── docker-compose.yml
├── Dockerfile.prod (frontend)
└── pyproject.toml            # Ruff linter config
```

---

## Key Patterns

### Dependency Injection

Every route declares its dependencies explicitly — no globals, no manual wiring:

```python
@router.get("/products/{slug}", response_model=ProductResponse)
async def get_product(
    slug: str,
    db: AsyncSession = Depends(get_db),              # session injected
    current_user = Depends(get_current_active_user), # JWT decoded, user loaded
):
    ...
```

`require_role()` is a factory that returns a dependency checking the user's role:

```python
@router.post("/products", response_model=ProductResponse)
async def create_product(
    current_user = Depends(require_role("seller", "admin")),  # 403 if buyer
):
    ...
```

### Async Database

Every database call uses `async/await`. Sync SQLAlchemy blocks the event loop:

```python
# Correct
result = await db.execute(select(Product).where(Product.slug == slug))
product = result.scalar_one_or_none()

# Never do this — blocks all concurrent requests
product = db.query(Product).filter_by(slug=slug).first()
```

### Redis Caching

Frequently-read data is cached with a key that encodes all query parameters:

```python
cache_key = "products:list:" + hashlib.md5(params.encode()).hexdigest()
cached = await cache_get(cache_key)
if cached:
    return json.loads(cached)        # no DB query

# ... DB query ...
await cache_set(cache_key, result.model_dump_json(), ttl=120)
```

Cache is explicitly invalidated on every write: `await cache_delete_pattern("products:list:*")`

### SELECT FOR UPDATE (Stock Race Condition)

During checkout, stock is decremented under a row-level lock to prevent oversell:

```python
result = await db.execute(
    select(Product).where(Product.id == product_id).with_for_update()
)
locked_product = result.scalar_one_or_none()
locked_product.stock -= quantity   # safe — row locked until commit
await db.commit()
```

### Price Snapshot

`OrderItem.unit_price` is copied from `product.price` at checkout time and never updated again. Past order totals are correct even if the seller later changes the price.

### Verified Purchase Reviews

Before accepting a review, the API checks whether the buyer actually received the product:

```python
is_verified = bool(await db.execute(
    select(exists().where(
        Order.buyer_id == current_user.id,
        Order.status == "delivered",
        OrderItem.order_id == Order.id,
        OrderItem.product_id == product_id,
    ))
))
```

### Alembic Migrations

Never modify tables by hand. Always generate and apply a migration:

```bash
alembic revision --autogenerate -m "add field_name to table_name"
# Review the generated file in alembic/versions/, then:
alembic upgrade head
```

---

## API Reference

Base URL: `http://localhost:8000/api/v1`
Interactive docs: **http://localhost:8000/docs**

### Authentication

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | None | Create buyer account, returns tokens |
| POST | `/auth/login` | None | Get access + refresh tokens (rate-limited: 5/min per IP) |
| POST | `/auth/refresh` | None | Exchange refresh token for new access token |
| POST | `/auth/logout` | Bearer | Logout (client discards tokens) |
| GET | `/auth/me` | Bearer | Current user profile |
| PATCH | `/auth/me` | Bearer | Update name / avatar / password |

**Swagger auth:** POST `/auth/login` with JSON body → copy `access_token` → click Authorize → paste in **HTTPBearer** field (not the OAuth2 form).

### Products

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/products` | None | List active products (filterable, paginated, searchable) |
| GET | `/products/my` | seller | Seller's own products |
| GET | `/products/{slug}` | None | Product detail with reviews |
| POST | `/products` | seller | Create product with images (multipart, max 5 images, 5MB each) |
| PUT | `/products/{id}` | seller (own) | Update product details |
| PATCH | `/products/{id}/status` | seller (own) | Change status: draft / active / archived |
| DELETE | `/products/{id}` | seller (own) | Soft-delete (archived) |

**Product filters** (`GET /products`):

```
?q=wireless+earbuds        full-text search via Elasticsearch
?category=smartphones      filter by category slug
?min_price=500&max_price=5000
?sort=newest|price_asc|price_desc|rating
?page=1&per_page=20
```

### Cart

Cart is stored in Redis (not the database), tied to the user's JWT identity.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/cart` | Bearer | Get cart with live product data and stale item cleanup |
| POST | `/cart/items` | Bearer | Add item or increase quantity |
| PUT | `/cart/items/{product_id}` | Bearer | Set exact quantity |
| DELETE | `/cart/items/{product_id}` | Bearer | Remove item |
| DELETE | `/cart` | Bearer | Clear entire cart |

### Orders

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/orders/checkout` | buyer | Create order + Razorpay payment from cart |
| POST | `/orders/webhook` | None | Razorpay webhook (HMAC-SHA256 verified) |
| GET | `/orders` | buyer / seller | List own orders |
| GET | `/orders/{id}` | buyer (own) / admin | Order detail |
| PATCH | `/orders/{id}/status` | seller / admin | Advance status |
| POST | `/orders/{id}/cancel` | buyer (pending) / admin | Cancel + refund |

### Reviews

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/products/{id}/reviews` | None | List reviews + rating summary |
| POST | `/products/{id}/reviews` | buyer | Submit review (one per buyer per product) |
| PUT | `/products/{id}/reviews/{rid}` | owner | Edit your review |
| DELETE | `/products/{id}/reviews/{rid}` | owner / admin | Delete review |
| POST | `/reviews/{id}/helpful` | Bearer | Mark review as helpful |

### Admin

All admin routes require `role=admin`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/admin/stats` | Platform stats: users, orders, revenue (this month vs last) |
| GET | `/admin/users` | All users, filterable by role + search |
| PATCH | `/admin/users/{id}` | Update role or active status (blocks self-role change) |
| GET | `/admin/products` | All products, all statuses |
| PATCH | `/admin/products/{id}/status` | Approve (active) or archive |
| GET | `/admin/orders` | All orders with filters |
| GET | `/admin/reviews` | All reviews, filterable by min_rating |
| DELETE | `/admin/reviews/{id}` | Delete any review |

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

Razorpay is India's standard payment gateway: UPI, cards, net banking, wallets.

```
1. Buyer adds items to cart

2. POST /orders/checkout (buyer only)
   → Validate stock (SELECT FOR UPDATE — race condition safe)
   → Calculate: subtotal + 18% GST + ₹50 shipping (free over ₹500)
   → razorpay.order.create(amount_paise, currency="INR")
   → Save Order (status=pending) with razorpay_order_id
   → Return { razorpay_order_id, amount_paise, razorpay_key_id }

3. Frontend opens Razorpay checkout modal
   → new window.Razorpay({ key, amount, order_id, handler })
   → rzp.open()

4. Buyer completes payment

5. Razorpay POSTs to POST /orders/webhook
   → Verify X-Razorpay-Signature (HMAC-SHA256 of raw body bytes)
   → payment.captured → order=paid → trigger confirmation email (Celery)
   → payment.failed   → order=cancelled → restore stock
```

**Local webhook testing:**

```bash
ngrok http 8000
# Add https://xxxx.ngrok.io/api/v1/orders/webhook to Razorpay Dashboard
# → Settings → Webhooks → Add Webhook
# → Subscribe: payment.captured, payment.failed
```

---

## Email and Background Tasks

Emails are sent via **Resend** — no SMTP, no configuration. All email sends are offloaded to Celery so the API response is not delayed.

```python
# Webhook handler — fire and forget
send_order_confirmation_email.delay(str(order.id))

# Celery task — single asyncio.run() (two calls cause event loop crash with asyncpg)
async def _fetch():
    async with AsyncSessionLocal() as db:
        order = await get_order(db, order_id)
        user = await get_user_by_id(db, order.buyer_id)
        return order, user

order, user = asyncio.run(_fetch())
resend.Emails.send({"from": ..., "to": [user.email], "subject": ..., "html": ...})
```

**Tasks:**
- `send_order_confirmation_email` — triggered by `payment.captured` webhook
- `send_shipping_notification_email` — triggered when status advances to `shipped`
- `send_welcome_email` — triggered on registration

**Run the worker:**

```bash
cd backend
celery -A app.tasks.celery_app worker -l info --concurrency 2
```

---

## Testing

Tests hit a real PostgreSQL database — not mocks. This catches issues that in-memory fakes miss.

```bash
# Run from the project root (not backend/)
backend\.venv\Scripts\python.exe -m pytest tests/ -q          # Windows
python -m pytest tests/ -q                                     # Mac/Linux (venv active)

# With coverage
backend\.venv\Scripts\python.exe -m pytest tests/ -q --cov=app --cov-report=term-missing

# Single file
backend\.venv\Scripts\python.exe -m pytest tests/test_auth.py -v --tb=short
```

**Status: 105 tests, all passing.**

Every test gets a clean database — `conftest.py` truncates all tables after each test. Fixtures provide everything needed:

```python
async def test_create_product_as_seller(async_client, seller_token, test_db):
    response = await async_client.post(
        "/api/v1/products",
        data={"title": "Test Product", "price": "999", "stock": "10"},
        headers={"Authorization": f"Bearer {seller_token}"},
    )
    assert response.status_code == 201
```

**Test coverage targets per route:**

| Case | What it checks |
|---|---|
| Happy path | Route works with valid input |
| Unauthenticated | Returns 401 with no token |
| Wrong role | Returns 403 for buyer calling seller route |
| Not found | Returns 404 for missing resource |
| Conflict | Returns 409 for duplicates |

---

## Development Tasks

### Add a field to a model

1. Edit the model in `backend/app/models/`
2. Edit the Pydantic schema in `backend/app/schemas/`
3. Generate and apply migration:
   ```bash
   alembic revision --autogenerate -m "add field to table"
   alembic upgrade head
   ```
4. Update the CRUD function if needed
5. Write or update tests

### Add a new route

1. Add to the relevant file in `backend/app/api/v1/`
2. Register the router in `backend/app/main.py` if it's a new file
3. Add schemas, CRUD function
4. Write tests in `tests/test_<resource>.py`

### Reset the database

```bash
docker compose down -v
docker compose up -d postgres redis elasticsearch
cd backend
alembic upgrade head
python seed.py
```

### Check and fix lint errors

```bash
ruff check backend/app/          # show errors
ruff check backend/app/ --fix    # auto-fix safe errors
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Database (pre-configured for Docker)
DATABASE_URL=postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200

# Auth — generate: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<your-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Razorpay — https://dashboard.razorpay.com/app/keys
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...

# Resend — https://resend.com/api-keys
RESEND_API_KEY=re_...
EMAIL_FROM=onboarding@resend.dev
TEST_EMAIL_OVERRIDE=   # dev only: redirect all mail here (Resend test mode restriction)

# AWS S3 — or set USE_LOCAL_STORAGE=true to save files locally
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1
S3_BUCKET_NAME=your-bucket-name
USE_LOCAL_STORAGE=false

# Sentry — leave blank to disable
SENTRY_DSN=

# CORS
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## CI/CD

GitHub Actions runs on every push to `main` or `develop` and on all pull requests.

| Job | What it does |
|---|---|
| `backend-test` | Spins up PostgreSQL + Redis, installs deps, runs 105 pytest tests |
| `backend-lint` | Runs ruff (E, W, F rules, ignores E501) |
| `frontend-build` | TypeScript type check + Vite production build |

A green run means: tests pass, code is lint-clean, frontend compiles without errors.

**Production Dockerfiles** (`backend/Dockerfile.prod`, `frontend/Dockerfile.prod`) are ready but deployment is not yet configured. The frontend Dockerfile uses nginx with SPA fallback and 1-year asset cache headers.
