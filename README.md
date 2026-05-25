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

PyMart is a multi-category e-commerce platform designed for India. Buyers discover products through full-text search, add them to a persistent cart, and pay via Razorpay (UPI, cards, net banking, wallets). Sellers manage their listings from a dedicated dashboard and receive real-time WebSocket notifications when an order is placed. Admins moderate the platform through a built-in panel covering users, products, orders, and reviews.

The entire system is asynchronous end to end: the FastAPI backend uses `async/await` throughout, Celery handles email delivery without blocking the request path, and Elasticsearch powers instant full-text search. The frontend stays in sync without polling — WebSocket events update the order timeline and notification bell the moment a payment is captured.

---

## Architecture

```
Browser
  │
  ├─── HTTPS ──► Vercel (React 19 + Vite)
  │                  │
  │          REST / WebSocket
  │                  │
  └─── ─────────► FastAPI / uvicorn  ◄─── Razorpay webhook
                     │
          ┌──────────┼──────────────┬────────────────┐
          │          │              │                │
       PostgreSQL  Redis        Elasticsearch     AWS S3
        primary DB  cart + cache   product search   images
                    rate limits
                    Celery broker
                         │
                  Celery Worker
                         │
                      Resend API
                   (transactional email)
```

All five backend services run as Docker containers in local development:

| Container | Image | Role |
|-----------|-------|------|
| `backend` | `Dockerfile` | FastAPI + uvicorn (async HTTP + WebSocket) |
| `celery_worker` | `Dockerfile` | Celery worker for email tasks |
| `postgres` | `postgres:16` | Primary database |
| `redis` | `redis:7` | Cache, cart storage, Celery broker |
| `elasticsearch` | `elasticsearch:8.12.0` | Full-text product search |

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
| Validation | Pydantic v2 | 2.x | Request/response schemas |
| Monitoring | Sentry + Prometheus | latest | Error tracking + metrics |
| Frontend | React | 19.2 | SPA with server-state sync |
| Build tool | Vite | 8.x | Sub-second HMR, optimised prod builds |
| Language | TypeScript | 6.x | End-to-end type safety |
| Styling | Tailwind CSS | 4.x | Utility-first design system |
| Server state | TanStack React Query | 5.x | Cache, background refetch, mutations |
| Client state | Zustand | 5.x | Auth, cart, notification stores |
| HTTP client | Axios | 1.x | Auto token refresh interceptor |
| Containerisation | Docker + Compose v2 | — | All 5 backend services containerised |
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
├── docker-compose.yml             # all 5 services: backend, celery_worker, postgres, redis, elasticsearch
├── .env.example
└── pytest.ini                     # asyncio_mode=auto, pythonpath=. backend
```

---

## Key Technical Decisions

### 1. Async FastAPI over Django

FastAPI's native `async/await` support means a single worker process can handle hundreds of concurrent requests without thread-pool overhead. Combined with `asyncpg` (the fastest PostgreSQL driver for Python), the database layer adds zero synchronous blocking. FastAPI also generates OpenAPI 3.0 docs automatically — the Swagger UI works out of the box.

### 2. Redis for the Cart (not PostgreSQL)

Carts are ephemeral, user-scoped, and written far more frequently than they are read in aggregate. A Redis hash per user (`cart:{user_id}`) with a 30-day TTL gives O(1) reads/writes (`HGET`/`HSET`), automatic expiry without a cleanup job, and zero load on PostgreSQL for a high-frequency operation. Stale items (sold-out or archived products) are cleaned up lazily on each `GET /cart`.

### 3. SELECT FOR UPDATE in Checkout

Concurrent checkouts for the same product without a lock would allow overselling. `SELECT ... FOR UPDATE` in checkout acquires a row-level lock on each product row before decrementing stock, serialising concurrent checkout attempts for the same product. The lock is held only for the duration of the stock update — typically microseconds.

### 4. Celery for Email Delivery

Sending an email inline with the order webhook response would add 200–500 ms of Resend API latency to every successful payment event. With Celery, the webhook handler queues the email task and returns `{"status": "ok"}` in under 10 ms. Tasks are configured with `max_retries=3, default_retry_delay=60` for automatic retry on Resend downtime.

**Engine-per-task pattern:** Celery prefork workers are forked processes. The global async SQLAlchemy engine created at import time binds its connection pool to the parent process's event loop. When a forked worker calls `asyncio.run()`, Python creates a new event loop — reusing the parent's engine connections raises `RuntimeError: got Future attached to a different loop`. The fix is a fresh `create_async_engine()` scoped inside each task's coroutine, disposed immediately after the query.

### 5. Razorpay Webhook Signature Verification

Razorpay signs webhook payloads with HMAC-SHA256 of the raw request body using the key secret. The `/orders/webhook` endpoint verifies this signature before processing any event — preventing spoofed webhook calls that could mark orders as paid without actual payment. The raw body bytes are captured before JSON parsing (parsing modifies whitespace) and verified via the Razorpay SDK's `verify_webhook_signature` utility.

### 6. SQLAlchemy 2.x `mapped_column()` and `Mapped[T]`

The 2.x ORM API uses Python type annotations directly (`Mapped[Optional[str]]`) rather than the old `Column(String, nullable=True)` form. IDEs understand column types without plugins, mypy can type-check ORM queries, and the `DeclarativeBase` approach eliminates the `Base = declarative_base()` metaclass pattern.

### 7. Elasticsearch for Product Search

`ILIKE '%query%'` on a PostgreSQL `products` table degrades to sequential scans at scale. Elasticsearch's `multi_match` query provides relevance scoring (title matches score 3×, tags 2×, description 1×) and efficient filter combinations via the bool/filter DSL. Elasticsearch is treated as non-critical: if the service is unavailable, the endpoint falls back to a DB query — the platform remains functional during ES downtime.

---

## Security

| Measure | Implementation |
|---------|----------------|
| Password hashing | bcrypt via passlib (`bcrypt<4.0.0` pinned for compatibility) |
| Session tokens | JWT access (30 min) + refresh (7 days); stateless, rotation on refresh |
| Webhook integrity | Razorpay HMAC-SHA256 signature verified on every incoming webhook |
| Login rate limiting | Redis counter per IP: 5 attempts / 60 seconds; counter reset on success |
| SQL injection | SQLAlchemy ORM only — no raw SQL anywhere in the codebase |
| CORS | Explicit `ALLOWED_ORIGINS` list — never `allow_origins=["*"]` |
| Secrets management | All credentials from environment variables; `.env` is gitignored |
| Race condition prevention | `SELECT FOR UPDATE` row lock during stock decrement at checkout |
| Ownership enforcement | Sellers can only modify their own products; buyers can only cancel their own orders |
| Soft deletes | Products are archived, not hard-deleted — data is retained for order history |
| Input validation | Pydantic v2 validates every request body; `@field_validator` for custom rules |
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
```

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.

---

<div align="center">
Built with FastAPI, React, and ☕
</div>
