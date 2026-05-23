# 🛒 PyMart

> A production-ready, full-stack e-commerce platform built for the Indian market — real-time order tracking, Razorpay payments, Elasticsearch search, and a role-based seller/admin system.

[![CI](https://github.com/gautam-oss/PyMart/actions/workflows/ci.yml/badge.svg)](https://github.com/gautam-oss/PyMart/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Overview

PyMart is a multi-category e-commerce platform designed for India. Buyers discover products through full-text search, add them to a persistent cart, and pay via Razorpay (UPI, cards, net banking, wallets — all Indian payment methods). Sellers manage their listings from a dedicated dashboard and receive real-time WebSocket notifications when an order is placed. Admins moderate the platform through a built-in panel covering users, products, orders, and reviews.

The entire system is asynchronous end to end: the FastAPI backend uses `async/await` throughout (no sync database calls), Celery handles email delivery without blocking the request path, and Elasticsearch powers instant full-text search. The frontend stays in sync without polling — WebSocket events update the order timeline and notification bell the moment a payment is captured.

**Who it's for:** Indian sellers who need a quick path to market, and buyers who want a clean, fast shopping experience with familiar Indian payment options.

---

## Architecture

```
Browser
  │
  ├─── HTTPS ──► Vercel (React 19 + Vite)
  │                  │
  │          REST / WebSocket
  │                  │
  └─── ─────────► Render (FastAPI / uvicorn)
                     │
          ┌──────────┼──────────────┬────────────────┐
          │          │              │                │
    Supabase      Upstash        Bonsai.io       AWS S3
   (PostgreSQL)   (Redis)     (Elasticsearch)   (Mumbai)
    primary DB    cart + cache   product search   images
                  rate limits
                  Celery broker

                     │
              Celery Worker (Render)
                     │
                  Resend API
                 (transactional email)

Razorpay ──── webhook ──► FastAPI /api/v1/orders/webhook
                              │
                    verify HMAC-SHA256
                              │
                    update Order status
                              │
                   send WebSocket event
                              │
                   queue email task (Celery)
```

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Backend framework | FastAPI + uvicorn | latest | Async HTTP + WebSocket server |
| Language | Python | 3.12 | Type-safe async backend |
| ORM | SQLAlchemy asyncio | 2.x | Async DB access, type-mapped models |
| DB driver | asyncpg | latest | High-performance PostgreSQL adapter |
| Migrations | Alembic | latest | Schema versioning |
| Database | PostgreSQL | 16 | Primary data store |
| Cache / Queue | Redis | 7 | Cart storage, response cache, Celery broker |
| Search | Elasticsearch | 8.12.0 | Full-text product search with relevance scoring |
| Task queue | Celery | latest | Async email delivery |
| Payments | Razorpay | latest | INR payments (UPI, cards, wallets) |
| Email | Resend SDK | latest | Transactional email |
| Image storage | AWS S3 (ap-south-1) | — | Product image CDN |
| Auth | python-jose + passlib | latest | JWT access/refresh tokens + bcrypt |
| Validation | Pydantic v2 | 2.x | Request/response schemas, 5–17× faster than v1 |
| Monitoring | Sentry + Prometheus | latest | Error tracking + metrics |
| Frontend | React | 19.2 | SPA with server-state sync |
| Build tool | Vite | 8.x | Sub-second HMR, optimised prod builds |
| Language | TypeScript | 6.x | End-to-end type safety |
| Styling | Tailwind CSS | 4.x | Utility-first design system |
| Server state | TanStack React Query | 5.x | Cache, background refetch, mutations |
| Client state | Zustand | 5.x | Auth, cart, notification stores |
| HTTP client | Axios | 1.x | Auto token refresh interceptor |
| Icons | Lucide React | 1.x | Consistent icon system |
| Charts | Recharts | 3.x | Admin revenue charts |
| Routing | React Router | 7.x | File-based SPA routing |
| Containerisation | Docker + Compose v2 | — | Local dev parity |
| CI/CD | GitHub Actions | — | Test + lint + build on every push |

---

## Features

| Buyer | Seller | Admin |
|-------|--------|-------|
| Browse products by category | Create and manage product listings | Full user management (role + active status) |
| Full-text search (Elasticsearch) | Upload up to 5 product images (5 MB each) | Moderate all products (status override) |
| Filter by price range and category | Toggle product status (draft / active / archived) | View and manage all orders |
| Persistent cart (30-day Redis TTL) | View orders containing their products | Delete any review |
| 3-step checkout wizard | Advance order status (processing → shipped → delivered) | Platform stats: revenue, user counts, orders by status |
| Razorpay payment (UPI / card / wallet) | Real-time notification when a new order is placed | Month-on-month revenue comparison |
| Real-time order status notifications (WebSocket) | Seller analytics dashboard | |
| Order tracking timeline (5-step visual) | | |
| Submit product reviews (verified purchase detection) | | |
| Mark reviews as helpful | | |
| Cancel pending orders (auto-refund if paid) | | |
| Profile management | | |

---

## API Reference

All endpoints are prefixed `/api/v1`. Authentication uses `Authorization: Bearer <access_token>`.

### Auth

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | — | Register buyer; returns `access_token` + `refresh_token` |
| `POST` | `/auth/login` | — | Login; rate-limited to 5 attempts / 60 s per IP |
| `POST` | `/auth/refresh` | — | Exchange `refresh_token` for new token pair |
| `POST` | `/auth/logout` | Required | Invalidate session (client discards tokens) |
| `GET` | `/auth/me` | Required | Current user profile |
| `PATCH` | `/auth/me` | Required | Update profile (name, avatar) |

### Products

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/products` | — | List active products; `?q=` routes through Elasticsearch |
| `GET` | `/products/my` | seller/admin | Seller's own products (all statuses) |
| `GET` | `/products/{slug}` | — | Product detail; cached 5 min in Redis |
| `POST` | `/products` | seller/admin | Create product (`multipart/form-data`, up to 5 images) |
| `PUT` | `/products/{id}` | seller/admin | Update product details (ownership enforced) |
| `PATCH` | `/products/{id}/status` | seller/admin | Change status: `draft` / `active` / `archived` |
| `DELETE` | `/products/{id}` | seller/admin | Soft-delete + remove from Elasticsearch index |

### Categories

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/categories` | — | Full category tree; cached 1 h in Redis |
| `GET` | `/categories/{slug}` | — | Single category |
| `POST` | `/categories` | admin | Create category |
| `PUT` | `/categories/{id}` | admin | Update category |
| `DELETE` | `/categories/{id}` | admin | Delete (blocked if category has active products) |

### Cart

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/cart` | Required | Get cart; stale items removed automatically |
| `POST` | `/cart/items` | Required | Add item (capped at available stock) |
| `PUT` | `/cart/items/{product_id}` | Required | Update quantity; `quantity=0` removes item |
| `DELETE` | `/cart/items/{product_id}` | Required | Remove single item |
| `DELETE` | `/cart` | Required | Clear entire cart |

### Orders

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/orders` | Required | Buyer: own orders. Seller: orders with their products |
| `GET` | `/orders/{id}` | Required | Order detail with items and tracking timestamps |
| `POST` | `/orders/checkout` | buyer | Create order + Razorpay order; clears cart |
| `POST` | `/orders/webhook` | — | Razorpay webhook (HMAC-SHA256 verified) |
| `PATCH` | `/orders/{id}/status` | seller/admin | Advance status: `paid → processing → shipped → delivered` |
| `POST` | `/orders/{id}/cancel` | Required | Cancel order; issues Razorpay refund if already paid |

### Reviews

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/products/{id}/reviews` | — | Paginated reviews + rating summary (average, breakdown) |
| `POST` | `/products/{id}/reviews` | buyer | Submit review; one per product; auto-detects verified purchase |
| `PUT` | `/products/{id}/reviews/{rid}` | Required | Edit own review |
| `DELETE` | `/products/{id}/reviews/{rid}` | Required | Delete own review; admin can delete any |
| `POST` | `/reviews/{id}/helpful` | Required | Mark review helpful (not own) |

### Admin

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/admin/users` | admin | Paginated user list; filter by role |
| `PATCH` | `/admin/users/{id}` | admin | Update role or active status |
| `GET` | `/admin/products` | admin | All products (all statuses) |
| `PATCH` | `/admin/products/{id}/status` | admin | Override product status |
| `GET` | `/admin/orders` | admin | All orders; filter by status or buyer |
| `GET` | `/admin/stats` | admin | Revenue (this month / last month), user counts, orders by status |
| `GET` | `/admin/reviews` | admin | All reviews; filter by minimum rating |
| `DELETE` | `/admin/reviews/{id}` | admin | Remove any review |

### WebSocket + System

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `WS` | `/ws?token=<jwt>` | JWT in query | Real-time events: `order.paid`, `order.placed`, `order.status_changed`, `order.cancelled` |
| `GET` | `/health` | — | `{status, db, redis}` — used by UptimeRobot / load balancer |
| `GET` | `/metrics` | — | Prometheus metrics (via prometheus-fastapi-instrumentator) |
| `GET` | `/docs` | — | Swagger UI with HTTPBearer auth |

---

## Project Structure

```
PyMart/
├── .github/
│   └── workflows/ci.yml          # 3-job pipeline: test → lint → build
├── backend/
│   ├── Dockerfile                # dev image (uvicorn --reload)
│   ├── Dockerfile.prod           # multi-stage, non-root, production
│   ├── requirements.txt          # Python dependencies
│   ├── seed.py                   # dev data seeder (6 users, 14 products, orders)
│   ├── alembic.ini
│   ├── alembic/versions/         # 2 migration files
│   └── app/
│       ├── main.py               # app factory, middleware, router registration
│       ├── core/
│       │   ├── config.py         # pydantic-settings (reads .env automatically)
│       │   ├── database.py       # async SQLAlchemy engine + session factory
│       │   ├── security.py       # JWT encode/decode + bcrypt helpers
│       │   ├── redis.py          # aioredis connection pool + cache helpers
│       │   ├── deps.py           # FastAPI dependency injection (auth, roles)
│       │   └── websocket.py      # ConnectionManager (multi-tab aware)
│       ├── api/v1/               # route handlers (one file per domain)
│       │   ├── auth.py           # register, login, refresh, logout
│       │   ├── products.py       # CRUD + image upload + search
│       │   ├── categories.py     # category tree management
│       │   ├── cart.py           # Redis cart operations
│       │   ├── orders.py         # checkout, webhook, status transitions
│       │   ├── reviews.py        # reviews + helpful votes
│       │   ├── users.py          # user profile endpoints
│       │   ├── admin.py          # admin CRUD + stats
│       │   └── ws.py             # WebSocket endpoint
│       ├── models/               # SQLAlchemy ORM (all imported in __init__.py)
│       │   ├── user.py           # User (roles: buyer/seller/admin)
│       │   ├── category.py       # Category (self-referential tree)
│       │   ├── product.py        # Product (images + tags as JSON columns)
│       │   ├── order.py          # Order + OrderItem (3 timestamp columns)
│       │   └── review.py         # Review (unique per user+product)
│       ├── schemas/              # Pydantic v2 request/response shapes
│       ├── crud/                 # pure async DB query functions
│       ├── services/
│       │   ├── razorpay.py       # order creation, webhook verification, refund
│       │   ├── storage.py        # S3 upload with Pillow resize (1200×1200)
│       │   ├── search.py         # Elasticsearch index + search service
│       │   └── cart.py           # CartService (Redis hash, stale cleanup)
│       └── tasks/
│           ├── celery_app.py     # Celery config (Redis broker, Asia/Kolkata timezone)
│           └── email_tasks.py    # order confirmation + shipping notification emails
├── frontend/
│   ├── index.html                # Razorpay checkout.js script tag lives here
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx               # router: public + ProtectedRoute + RoleRoute + AdminLayout
│       ├── api/
│       │   └── client.ts         # Axios instance with automatic 401 → token refresh
│       ├── components/
│       │   ├── Navbar.tsx         # top nav: WebSocket hook, notification bell, cart badge
│       │   ├── NotificationBell.tsx # real-time bell (50-item ring buffer, unread badge)
│       │   ├── ProtectedRoute.tsx # redirect to /login if not authenticated
│       │   ├── RoleRoute.tsx      # redirect if role doesn't match
│       │   └── Toast.tsx          # toast notification system
│       ├── hooks/
│       │   ├── useWebSocket.ts    # WS with exponential backoff reconnect (max 30 s, 5 retries)
│       │   └── useOrders.ts       # React Query hooks for orders
│       ├── pages/
│       │   ├── CheckoutPage.tsx   # 3-step: cart review → address → Razorpay payment
│       │   ├── OrderDetailPage.tsx # order tracking timeline (5 steps + terminal state)
│       │   ├── seller/            # SellerDashboard, SellerProducts, CreateProduct, EditProduct
│       │   └── admin/             # AdminLayout, Dashboard, Users, Products, Orders, Reviews
│       ├── store/
│       │   ├── authStore.ts       # Zustand + localStorage persist
│       │   ├── cartStore.ts       # Zustand cart snapshot
│       │   └── notificationStore.ts # Zustand, 50-item ring buffer
│       └── types/index.ts         # TypeScript interfaces mirroring all backend schemas
├── tests/                         # 108 async tests
│   ├── conftest.py                # fixtures: async_client, buyer/seller/admin tokens
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_orders.py
│   ├── test_cart.py
│   ├── test_categories.py
│   ├── test_reviews.py
│   ├── test_admin.py
│   ├── test_order_status.py
│   └── test_websocket.py          # sync WebSocket tests via Starlette TestClient
├── docker-compose.yml             # postgres:16, redis:7, elasticsearch:8.12, backend, celery_worker
├── .env.example
└── pytest.ini                     # asyncio_mode=auto, pythonpath=. backend
```

---

## Getting Started

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |
| Docker Desktop | latest | WSL2 backend on Windows |
| Git | any | |

You also need accounts for: **Razorpay** (test mode), **Resend** (free tier), and **AWS S3** (free tier). See [Environment Variables](#environment-variables) for each variable.

### Local Development

```bash
# 1. Clone and configure
git clone https://github.com/gautam-oss/PyMart.git
cd PyMart
cp .env.example .env
# Edit .env — fill in RAZORPAY, RESEND, AWS keys

# 2. Start infrastructure
docker compose up -d postgres redis elasticsearch

# 3. Backend
cd backend
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head          # run migrations
python seed.py                # optional: load demo data
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Celery worker (new terminal, venv active, from backend/)
celery -A app.tasks.celery_app worker -l info --concurrency 2

# 5. Frontend (new terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

**Swagger auth:** `POST /api/v1/auth/login` → copy `access_token` → Authorize → paste in **HTTPBearer** field (not the OAuth2 form).

### Docker (all services)

```bash
docker compose up -d
# Backend:  http://localhost:8000
# Frontend: run npm run dev separately (or add to compose)
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values below.

### Database

| Variable | Required | Description | Where to get |
|----------|----------|-------------|--------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/db` | Local: Docker. Prod: Supabase |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Local: Docker. Prod: Upstash |
| `ELASTICSEARCH_URL` | Yes | `http://localhost:9200` | Local: Docker. Prod: Bonsai.io |

### Auth

| Variable | Required | Description | Where to get |
|----------|----------|-------------|--------------|
| `SECRET_KEY` | Yes | 32-byte hex string | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | No | JWT algorithm (default: `HS256`) | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Access token TTL (default: `30`) | — |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | Refresh token TTL (default: `7`) | — |

### Payments

| Variable | Required | Description | Where to get |
|----------|----------|-------------|--------------|
| `RAZORPAY_KEY_ID` | Yes | `rzp_test_...` | [Razorpay Dashboard](https://dashboard.razorpay.com) → Settings → API Keys |
| `RAZORPAY_KEY_SECRET` | Yes | Key secret | Same as above |

### Email

| Variable | Required | Description | Where to get |
|----------|----------|-------------|--------------|
| `RESEND_API_KEY` | Yes | `re_...` | [Resend Dashboard](https://resend.com) → API Keys |
| `EMAIL_FROM` | No | Sender address (default: `onboarding@resend.dev`) | Use `onboarding@resend.dev` in test mode |
| `TEST_EMAIL_OVERRIDE` | No | Redirect all email to this address in dev | Your email — Resend test mode only delivers to account owner |

### Storage

| Variable | Required | Description | Where to get |
|----------|----------|-------------|--------------|
| `AWS_ACCESS_KEY_ID` | Yes | IAM access key | AWS Console → IAM → Users → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | Yes | IAM secret | Same as above |
| `AWS_REGION` | No | S3 region (default: `ap-south-1`) | — |
| `S3_BUCKET_NAME` | Yes | Bucket name | Create in AWS S3 console with public-read ACL |
| `USE_LOCAL_STORAGE` | No | Skip S3 upload in CI/dev (default: `false`) | Set `true` to skip S3 |

### Monitoring & App

| Variable | Required | Description | Where to get |
|----------|----------|-------------|--------------|
| `SENTRY_DSN` | No | Error tracking DSN | [Sentry](https://sentry.io) → New Project → FastAPI |
| `ALLOWED_ORIGINS` | No | CORS origins (default: `http://localhost:5173`) | Add prod frontend URL |

---

## Testing

```bash
# Run all 108 tests (from project root, not backend/)
backend\.venv\Scripts\python.exe -m pytest tests/ -q

# Verbose with coverage
backend\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing

# Single module
backend\.venv\Scripts\python.exe -m pytest tests/test_orders.py -v
```

**Results:** 108 tests, 0 failures, ~70 seconds on first run (DB setup) / ~15 s on subsequent runs.

| Test file | Coverage |
|-----------|----------|
| `test_auth.py` | register, login, rate limiting, refresh, /me |
| `test_products.py` | CRUD, ownership, image upload, 5MB limit |
| `test_orders.py` | checkout, stock decrement, webhook, cancel |
| `test_cart.py` | add, update, remove, stale cleanup, quantity cap |
| `test_categories.py` | tree, CRUD, active product guard |
| `test_reviews.py` | create, update, delete, helpful votes, uniqueness |
| `test_admin.py` | user management, product moderation, stats |
| `test_order_status.py` | all valid transitions, invalid transition rejection |
| `test_websocket.py` | valid token connects, invalid/missing token rejected (4008) |

Tests use a separate `pymart_test` PostgreSQL database. Each test truncates all tables + flushes Redis — full isolation, no teardown needed.

---

## Deployment

| Service | Platform | Free Tier |
|---------|----------|-----------|
| Backend API | [Render](https://render.com) | 750 h/month, sleeps after 15 min |
| Frontend | [Vercel](https://vercel.com) | Unlimited bandwidth |
| PostgreSQL | [Supabase](https://supabase.com) | 500 MB database, no sleep |
| Redis | [Upstash](https://upstash.com) | 10 000 commands/day |
| Elasticsearch | [Bonsai.io](https://bonsai.io) | Sandbox: 125 MB index |
| Keep-alive | [UptimeRobot](https://uptimerobot.com) | 50 monitors, 5-min interval |

**Deployment steps** are documented in `PROMPTS.md` (local, gitignored). Summary:

1. Provision Supabase (DB) + Upstash (Redis) + Bonsai.io (ES)
2. Deploy backend to Render — set all env vars, run `alembic upgrade head`
3. Deploy Celery worker to Render as a Background Worker
4. Deploy frontend to Vercel — set `VITE_API_URL` + `VITE_WS_URL`
5. Update Razorpay webhook URL to `https://your-backend.onrender.com/api/v1/orders/webhook`
6. Configure UptimeRobot to ping `/health` every 5 minutes

**Frontend env vars for production:**
```env
VITE_API_URL=https://your-backend.onrender.com
VITE_WS_URL=wss://your-backend.onrender.com
```

---

## Key Technical Decisions

### 1. Async FastAPI over Django

FastAPI's native `async/await` support means a single worker process can handle hundreds of concurrent requests without thread-pool overhead. Combined with `asyncpg` (the fastest PostgreSQL driver for Python), the database layer adds zero synchronous blocking. Django REST Framework, while excellent, would require `channels` for WebSocket support and `django-ninja` or similar for comparable API ergonomics. FastAPI also generates OpenAPI 3.0 docs automatically — the Swagger UI works out of the box.

### 2. Redis for the Cart (not PostgreSQL)

Carts are ephemeral, user-scoped, and written far more frequently than they are read in aggregate. A Redis hash per user (`cart:{user_id}`) with a 30-day TTL gives us: O(1) reads/writes (`HGET`/`HSET`), automatic expiry without a cleanup job, and zero load on PostgreSQL for a high-frequency operation. Stale items (sold-out or archived products) are cleaned up lazily on each `GET /cart` — the cart read path calls `get_products_by_ids` and removes any items whose products no longer exist or are inactive.

### 3. SELECT FOR UPDATE in Checkout

Concurrent checkouts for the same product without a lock would allow overselling. When two buyers simultaneously check out the last unit, a plain `UPDATE ... SET stock = stock - 1 WHERE stock > 0` might succeed twice at the read-committed isolation level. `SELECT ... FOR UPDATE` in checkout acquires a row-level lock on each product row before decrementing stock, serialising concurrent checkout attempts for the same product. The lock is held only for the duration of the stock update — typically microseconds — so it doesn't create a meaningful bottleneck.

### 4. Celery for Email Delivery

Sending an email inline with the order webhook response would add 200–500 ms of Resend API latency to every successful payment event. With Celery, the webhook handler queues the email task and returns `{"status": "ok"}` in under 10 ms. The Celery worker picks up the task from Redis, fetches order + user data in a single async database query, and sends the email. Tasks are configured with `max_retries=3, default_retry_delay=60` — if Resend is temporarily unavailable, the task retries automatically.

**Engine-per-task pattern:** Celery uses prefork workers — each worker is a forked process. The global async SQLAlchemy engine in `database.py` is created at import time and binds its connection pool to the parent process's event loop. When a forked worker calls `asyncio.run()`, Python creates a *new* event loop, and any attempt to reuse the parent's engine connections raises `RuntimeError: got Future attached to a different loop`. The fix is to create a fresh `create_async_engine()` inside each task's `_fetch()` coroutine — scoped to the same event loop that `asyncio.run()` creates — and `await engine.dispose()` immediately after the query.

### 5. Razorpay Webhook Signature Verification

Razorpay signs webhook payloads with an HMAC-SHA256 of the raw request body using the key secret. The `/orders/webhook` endpoint verifies this signature before processing any event. This prevents spoofed webhook calls that could mark orders as paid without actual payment. The raw body bytes are captured before JSON parsing (important — parsing modifies whitespace) and verified via the Razorpay SDK's `verify_webhook_signature` utility. An invalid signature returns 400 immediately; the order is never touched.

### 6. SQLAlchemy 2.x `mapped_column()` and `Mapped[T]`

The 2.x ORM API uses Python type annotations directly (`Mapped[Optional[str]]`) rather than the old `Column(String, nullable=True)` form. This means IDEs understand column types without plugins, mypy can type-check ORM queries, and the `DeclarativeBase` approach eliminates the `Base = declarative_base()` metaclass pattern. Every model column is explicitly typed, reducing an entire class of runtime surprises where `None` propagates unexpectedly from nullable columns.

### 7. Elasticsearch for Product Search

`ILIKE '%query%'` on a PostgreSQL `products` table works fine at hundreds of products but degrades to sequential scans at scale. Elasticsearch's `multi_match` query provides: relevance scoring (title matches score 3×, tags 2×, description 1×), BM25 ranking, and efficient filter combinations (status=active, stock>0, price range) via the bool/filter DST. Elasticsearch is treated as non-critical: if the service is unavailable, `products.py` falls back to a DB query. This means the platform remains functional during ES downtime — search results are just less relevant.

---

## Security

| Measure | Implementation |
|---------|----------------|
| Password hashing | bcrypt via passlib (`bcrypt<4.0.0` pinned for compatibility) |
| Session tokens | JWT access (30 min) + refresh (7 days); tokens are stateless, rotation on refresh |
| Webhook integrity | Razorpay HMAC-SHA256 signature verified on every incoming webhook |
| Login rate limiting | Redis counter per IP: 5 attempts / 60 seconds; counter reset on success |
| SQL injection | SQLAlchemy ORM only — no raw SQL anywhere in the codebase |
| CORS | Explicit `ALLOWED_ORIGINS` list — never `allow_origins=["*"]` |
| Secrets management | All credentials from environment variables; `.env` is gitignored |
| Race condition prevention | `SELECT FOR UPDATE` row lock during stock decrement at checkout |
| Ownership enforcement | Sellers can only modify their own products; buyers can only cancel their own orders |
| Soft deletes | Products are archived, not hard-deleted — data is retained for order history |
| Input validation | Pydantic v2 validates every request body; `@field_validator` for custom rules (e.g., 6-digit pincode) |
| Image validation | Content-type allow-list (JPEG/PNG/WebP); 5 MB size limit checked before S3 upload |
| Inactive account guard | `get_current_active_user` dependency rejects `is_active=False` users on every authenticated route |

---

## CI/CD Pipeline

The GitHub Actions pipeline runs on every push to `main`/`develop` and on every pull request targeting `main`. All 3 jobs must pass before merge.

```
push / PR
    │
    ├─── backend-test (ubuntu-latest)
    │       services: postgres:16, redis:7
    │       python: 3.12
    │       steps: pip install → pytest tests/ --cov=app
    │       env: all secrets injected as job env vars
    │       USE_LOCAL_STORAGE=true (skips S3)
    │
    ├─── backend-lint (ubuntu-latest)
    │       python: 3.12
    │       steps: pip install ruff → ruff check backend/app
    │       rules: E, W, F — ignore E501 (line length)
    │
    └─── frontend-build (ubuntu-latest)
            node: 20
            steps: npm ci → tsc --noEmit → npm run build
            Note: unused TypeScript declarations cause build failure
```

Secrets required in GitHub repo Settings → Secrets → Actions: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RESEND_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME`.

For CI, `USE_LOCAL_STORAGE=true` is hardcoded in the workflow — no S3 access required in tests.

---

## Contributing

```bash
# Fork the repo, then:
git checkout -b feat/your-feature-name
# Make changes
git commit -m "feat: description of what was added"
git push origin feat/your-feature-name
# Open a PR against main
```

**Branch naming:** `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`

**Commit convention:** [Conventional Commits](https://www.conventionalcommits.org) — `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`

**Before opening a PR:**
- `pytest tests/ -q` — all 108 tests must pass
- `ruff check backend/app --select E,W,F --ignore E501` — zero lint errors
- `npx tsc --noEmit` (from `frontend/`) — zero TypeScript errors

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
Built with FastAPI, React, and ☕
</div>
