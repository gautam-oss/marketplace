# Marketplace — Complete Architecture & Developer Education Guide

> Written from a fresh scan of every source file. This document is your complete reference
> for understanding not just WHAT the system does but WHY every decision was made.

---

## SECTION 1: THE BIG PICTURE

### 1.1 Full System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEVELOPER MACHINE                                  │
│                                                                                 │
│   git push origin main                                                          │
│         │                                                                       │
│         ▼                                                                       │
│   ┌──────────────┐                                                              │
│   │ GitHub Repo  │                                                              │
│   └──────┬───────┘                                                              │
│          │ triggers                                                             │
│          ▼                                                                      │
│   ┌──────────────────────────────────────────┐                                 │
│   │          GitHub Actions CI               │                                 │
│   │  ┌─────────────┐ ┌──────────┐ ┌───────┐ │                                 │
│   │  │backend-test │ │lint:ruff │ │ tsc + │ │                                 │
│   │  │ 108 tests   │ │ E,W,F    │ │ build │ │                                 │
│   │  └─────────────┘ └──────────┘ └───────┘ │                                 │
│   └──────────────────────────────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

                    PRODUCTION ARCHITECTURE
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   USER'S BROWSER                                                     │
│        │                                                             │
│        ├── HTTPS ──────────────────────────────────────────────┐    │
│        │                                                        │    │
│        ▼                                                        ▼    │
│  ┌─────────────────┐                          ┌─────────────────────┐│
│  │   VERCEL        │                          │   RENDER            ││
│  │   (Frontend)    │                          │   (Backend)         ││
│  │                 │  REST API + WebSocket    │                     ││
│  │  React 19       │◄────────────────────────►│  FastAPI + Uvicorn  ││
│  │  Vite 8         │                          │  :8000              ││
│  │  TypeScript 6   │                          │                     ││
│  │  Tailwind 4     │                          └──┬──────┬──────┬───┘│
│  │  Global CDN     │                             │      │      │    │
│  └─────────────────┘                             │      │      │    │
│                                                  │      │      │    │
│        ┌─────────────────────────────────────────┘      │      │    │
│        │                        ┌────────────────────────┘      │    │
│        │                        │               ┌───────────────┘    │
│        ▼                        ▼               ▼                    │
│  ┌──────────┐           ┌──────────────┐  ┌──────────┐             │
│  │ SUPABASE │           │   UPSTASH    │  │ BONSAI   │             │
│  │ Postgres │           │   Redis 7    │  │ Elastic  │             │
│  │    16    │           │              │  │ search   │             │
│  │ Tables:  │           │ Cart hashes  │  │ 8.12.0   │             │
│  │ users    │           │ Product cache│  │          │             │
│  │ products │           │ Category ttl │  │ Product  │             │
│  │ orders   │           │ Rate limits  │  │ full-text│             │
│  │ reviews  │           │ Celery broker│  │ search   │             │
│  │ categories│          └──────┬───────┘  └──────────┘             │
│  │ order_   │                  │                                    │
│  │ items    │                  ▼                                    │
│  └──────────┘         ┌──────────────────┐                         │
│                        │  RENDER          │                         │
│  ┌──────────┐           │  Celery Worker   │                         │
│  │ AWS S3   │           │  --concurrency 2 │                         │
│  │ Mumbai   │           └────────┬─────────┘                         │
│  │ap-south-1│                    │ calls                             │
│  │          │           ┌────────▼─────────┐                         │
│  │ Product  │           │   RESEND API     │                         │
│  │ images   │           │ transactional    │                         │
│  │ CDN URL  │           │ email delivery   │                         │
│  └──────────┘           └──────────────────┘                         │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    RAZORPAY                                  │   │
│  │  Browser ──opens modal──► Razorpay checkout.js              │   │
│  │  User pays (UPI / Card / Wallet)                             │   │
│  │  Razorpay ──POST webhook──► FastAPI /api/v1/orders/webhook  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  UPTIMEROBOT: pings /health every 5 min → prevents sleep    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 What Happens When a Buyer Uses the App — Full Code Trace

#### Step 1: Buyer Opens the Website

```
Browser → GET https://marketplace.vercel.app/
```

Vercel serves the pre-built React SPA (`frontend/dist/index.html`). This is pure HTML+JS —
no server-side rendering. The browser downloads a JavaScript bundle, React mounts, and the
router (`frontend/src/App.tsx`) renders the `<HomePage />`.

**HomePage** calls `useProducts()` from `frontend/src/hooks/useProducts.ts`, which fires:
```
GET /api/v1/products?page=1&per_page=20&sort=newest
```
Handler: `backend/app/api/v1/products.py → get_products()`

This checks the Redis cache first (`cache_get("products:list:{md5hash}")`) and if a cache
miss, queries PostgreSQL via `list_products()` in `backend/app/crud/product.py`.

The Axios client (`frontend/src/api/client.ts`) automatically attaches the Bearer token
from `localStorage.access_token` if the user is logged in.

#### Step 2: Buyer Searches for a Product

```
Browser → GET /api/v1/products?q=laptop&sort=newest&page=1
```

Handler: `backend/app/api/v1/products.py → get_products()` (line 99 — detects `q` parameter)

Because `q` is present, the handler calls:
```python
# products.py lines 100-115
es = get_es_client()
hits, total = await ElasticsearchService.search(es, q="laptop", ...)
```

Elasticsearch runs a `multi_match` query across `title^3`, `description`, `tags^2` fields
using BM25 scoring. The IDs returned by ES are then fetched from PostgreSQL in a single
`WHERE id IN (...)` query via `get_products_by_ids()` to get full ORM objects with relations.

The result is cached in Redis for 120 seconds with a key based on the MD5 hash of all query
parameters.

#### Step 3: Buyer Adds to Cart

```
Browser → POST /api/v1/cart/items
Body: {"product_id": "uuid", "quantity": 2}
```

Handler: `backend/app/api/v1/cart.py → add_to_cart()`

This calls `CartService.add_item()` in `backend/app/services/cart.py`. The service:
1. Validates the product exists and is `status=active`
2. Checks the buyer isn't trying to buy their own product
3. Calculates `new_qty = min(current + requested, product.stock)` to prevent over-adding
4. Executes `redis.hset(f"cart:{user_id}", str(product_id), new_qty)` — one Redis command
5. Sets `redis.expire(cart_key, 2592000)` — 30-day TTL

The cart is stored as a Redis Hash (not in PostgreSQL). No database write happens for cart
operations.

#### Step 4: Buyer Checks Out and Pays

**Sub-step 4a: Create Order**
```
Browser → POST /api/v1/orders/checkout
Body: {items: [...], shipping_address: {...}}
```

Handler: `backend/app/api/v1/orders.py → checkout()`

This is the most complex route. Here is exactly what happens:
1. For each item, `get_product_by_id()` validates: exists, active, not own product, stock >= qty
2. `subtotal = sum(price × qty)` in Python Decimal arithmetic
3. `shipping = ₹0 if subtotal > ₹500 else ₹50`
4. `tax = subtotal × 0.18` (GST 18%), quantized to 2 decimal places
5. `total = subtotal + shipping + tax`
6. `amount_paise = int(total × 100)` — Razorpay requires integers, no floats
7. `razorpay_service.create_order(amount_paise)` → SDK call to Razorpay API
8. **SELECT FOR UPDATE** — each product row is locked, stock decremented
9. `create_order()` writes Order + OrderItems to PostgreSQL
10. `CartService.clear_cart()` deletes the Redis hash
11. Returns `CheckoutResponse` to browser

**Sub-step 4b: User Pays in Razorpay Modal**

The frontend receives `{razorpay_order_id, amount, razorpay_key_id}` and calls:
```javascript
const rzp = new window.Razorpay({
    key: razorpay_key_id,
    amount: amount,          // in paise
    currency: "INR",
    order_id: razorpay_order_id,
    handler: (response) => { /* payment succeeded */ }
})
rzp.open()
```

`checkout.js` is loaded via a `<script>` tag in `frontend/index.html`.

**Sub-step 4c: Razorpay Sends Webhook**

After the user pays, Razorpay POSTs to:
```
POST /api/v1/orders/webhook
Headers: X-Razorpay-Signature: <hmac>
Body: {"event": "payment.captured", "payload": {...}}
```

Handler: `backend/app/api/v1/orders.py → razorpay_webhook()`

1. `verify_webhook_signature(body_bytes, signature)` — HMAC-SHA256 verification
2. Extract `order_id` from payload, find our Order by `razorpay_order_id`
3. Check `order.status == "pending"` — idempotency guard (handles duplicate webhooks)
4. `update_order_status(db, order, "paid", payment_id=..., paid_at=now)`
5. `ws_manager.send_to_user(buyer_id, {type: "order.paid", ...})` — WebSocket notification
6. For each seller: `ws_manager.send_to_user(seller_id, {type: "order.placed", ...})`
7. `send_order_confirmation_email.delay(str(order.id))` — queued to Redis/Celery

#### Step 5: Buyer Receives Confirmation Email

Celery worker (running on Render as a separate Background Worker service) picks up the task
from Redis. In `backend/app/tasks/email_tasks.py → send_order_confirmation_email()`:

```python
async def _fetch():
    async with AsyncSessionLocal() as db:
        order = await get_order(db, order_id)
        user = await get_user_by_id(db, order.buyer_id)
        return order, user

order, user = asyncio.run(_fetch())   # fetch everything in ONE asyncio.run()
recipient = settings.TEST_EMAIL_OVERRIDE or user.email

resend.Emails.send({
    "from": settings.EMAIL_FROM,
    "to": [recipient],
    "subject": f"Order Confirmed! #{str(order.id)[:8].upper()}",
    "html": html_body,
})
```

The request to the Razorpay webhook returned `{"status": "ok"}` within milliseconds —
email delivery happens entirely outside the request/response cycle.

---

## SECTION 2: PYTHON & FASTAPI DEEP DIVE

### 2.1 Why `async/await` Everywhere

#### What is the Event Loop?

Python's event loop is a single thread that juggles many tasks by pausing and resuming them.
When a task says `await some_io_operation()`, it's telling the event loop: "I'm waiting for
I/O (database, network, disk) — go run something else while I wait."

```
Event Loop Timeline (single thread):
─────────────────────────────────────────────────
Time 0ms: Request A arrives → start DB query A → AWAIT (pause A)
Time 0ms: Request B arrives → start DB query B → AWAIT (pause B)
Time 5ms: DB query A returns → resume A → send response A
Time 6ms: DB query B returns → resume B → send response B
─────────────────────────────────────────────────
Total time: 6ms to handle 2 requests
─────────────────────────────────────────────────
Sync equivalent (e.g. Django without ASGI):
Time 0ms: Request A arrives → start DB query A → BLOCK thread
Time 5ms: DB query A returns → send response A
Time 5ms: Request B starts being handled (was waiting)
Time 10ms: DB query B returns → send response B
─────────────────────────────────────────────────
Total time: 10ms to handle the same 2 requests
```

With sync Django and 10 threads: 10 concurrent requests max before queuing.
With async FastAPI: thousands of concurrent requests on 1 thread.

#### Our Actual Async Route vs Sync Equivalent

```python
# Our async route (products.py)
@router.get("/{slug}", response_model=ProductResponse)
async def get_product(slug: str, db: AsyncSession = Depends(get_db)):
    cached = await cache_get(f"products:slug:{slug}")  # async Redis
    if cached:
        return json.loads(cached)
    product = await get_product_by_slug(db, slug)      # async PostgreSQL
    await cache_set(...)                                # async Redis
    return product

# What sync would look like (WRONG — blocks the event loop)
@router.get("/{slug}", response_model=ProductResponse)
def get_product(slug: str, db: Session = Depends(get_db)):   # sync Session!
    product = db.query(Product).filter_by(slug=slug).first() # BLOCKING
    return product                                             # blocks all other requests
```

#### What Happens if You Use Sync DB in Async Route?

If you call `db.query(...)` (sync SQLAlchemy) inside an `async def` route, you **block
the entire event loop**. Every other request waiting for I/O is frozen. FastAPI will not
crash — it silently becomes as slow as Django with 1 thread. This is one of the hardest
bugs to diagnose.

SQLAlchemy 2.x's async engine (`create_async_engine`) will raise an error if you attempt
sync operations, which makes the bug visible rather than silent.

#### What is asyncpg and Why Not psycopg2?

`psycopg2` is the standard PostgreSQL driver for Python — it uses C-level blocking I/O.
Even inside an `async def`, a psycopg2 query blocks the OS thread.

`asyncpg` is written from scratch with `asyncio` in mind. It speaks the PostgreSQL wire
protocol without blocking, so `await db.execute(...)` genuinely releases the event loop
while waiting for PostgreSQL. It is also ~3× faster than psycopg2 on throughput benchmarks.

Our `DATABASE_URL` starts with `postgresql+asyncpg://` — this tells SQLAlchemy to use
asyncpg as the driver.

---

### 2.2 Pydantic v2 — The Complete Explanation

#### What is Schema Validation?

Every byte that enters our API from the internet is untrusted. Schema validation means:
"Before this data touches our database or business logic, verify it matches exactly what
we expect." Pydantic does this automatically by parsing the JSON body into Python objects.

#### The UserCreate Schema — Fully Annotated

```python
# backend/app/schemas/user.py

class UserBase(BaseModel):          # shared fields — used by inheritance
    email: EmailStr                 # Pydantic validates this is a real email address format
    full_name: str                  # required, any non-empty string


class UserCreate(UserBase):         # inherits email + full_name
    password: str                   # required

    @field_validator("password")    # runs AFTER type validation
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
            # FastAPI catches ValueError and returns 422 Unprocessable Entity
        return v                    # must return the value (can transform it here)
```

If someone POSTs `{"email": "not-an-email", "full_name": "x", "password": "abc"}`,
Pydantic raises a `ValidationError` before the route function even runs. FastAPI
automatically converts this to a `422` response with a JSON body explaining every error.

#### What is `ConfigDict(from_attributes=True)`?

SQLAlchemy ORM objects are Python objects with attributes (`user.email`, `user.id`).
Pydantic by default expects a dict: `{"email": "...", "id": "..."}`.

`from_attributes=True` tells Pydantic: "Also accept objects — read their attributes."

```python
# Without from_attributes=True → ERROR:
user = User(email="a@b.com", ...)  # SQLAlchemy object
UserResponse.model_validate(user)  # ValidationError: expected dict

# With from_attributes=True → works:
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email: str
    id: uuid.UUID

UserResponse.model_validate(user)  # reads user.email, user.id — works!
```

Every `*Response` schema in our codebase has this config because they serialize ORM objects.

#### Why Separate Create / Update / Response Schemas?

This is one of the most important patterns in the codebase:

```
UserCreate   → what the client SENDS to register (email, full_name, password)
UserUpdate   → what the client SENDS to update profile (all optional)
UserResponse → what the server RETURNS (id, email, role, is_active — but NOT password!)
UserPublic   → minimal data shown to other users (id, full_name, avatar_url only)
```

If we used one schema for everything:
- Returning `UserCreate` to the client would expose `hashed_password`
- Accepting `UserResponse` as input would let clients set their own `role`
- `UserUpdate` has all fields optional — `UserCreate` requires them

#### What is `Generic[T]` in PaginatedResponse?

```python
# backend/app/schemas/common.py
from typing import Generic, TypeVar
T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]   # T is a placeholder for any type
    total: int
    page: int
    per_page: int
    pages: int
```

This lets us write `PaginatedResponse[ProductListResponse]` or
`PaginatedResponse[OrderListResponse]` — one schema that works for any paginated list.
Without generics, we'd need `PaginatedProductResponse`, `PaginatedOrderResponse`, etc.

---

### 2.3 FastAPI Dependency Injection

#### What is `Depends()` and Why Is It Powerful?

`Depends()` is FastAPI's dependency injection system. It lets you declare that a route
function needs something (a database session, the current user, a Redis connection) and
FastAPI will compute and inject it automatically.

```python
# Without Depends — manual, repetitive, hard to test:
@router.get("/me")
async def get_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload.get("sub")
    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(db, user_id)
    return user

# With Depends — clean, reusable, testable:
@router.get("/me")
async def get_me(current_user = Depends(get_current_active_user)):
    return current_user
```

The `Depends(get_current_active_user)` version is:
- Reused by every authenticated endpoint without copy-pasting
- Mockable in tests (override the dependency, inject a fake user)
- Composable — dependencies can depend on other dependencies

#### Tracing `get_current_user()` Step by Step

```python
# backend/app/core/deps.py

# Step 1: oauth2_scheme reads "Authorization: Bearer <token>" from HTTP header
#         HTTPBearer does the same. Both are registered with Security().
#         FastAPI calls whichever one produces a non-None result.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    oauth2_token = Security(oauth2_scheme),      # tries OAuth2 form header
    bearer_creds = Security(bearer_scheme),       # tries Bearer header
    db: AsyncSession = Depends(get_db),           # injects DB session
):
    # Step 2: token = whichever scheme returned a value
    token = oauth2_token or (bearer_creds.credentials if bearer_creds else None)
    if not token:
        raise HTTPException(401, "Not authenticated")

    # Step 3: decode_token() verifies JWT signature + expiry
    #         If expired or tampered: raises 401 HTTPException
    payload = decode_token(token)
    user_id = payload.get("sub")          # our user's UUID is in "sub" claim

    # Step 4: DB query fetches the actual User object
    user = await get_user_by_id(db, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(401, "User not found")
    return user                           # this User object is injected into the route
```

#### The `require_role()` Factory Pattern

```python
def require_role(*roles: str) -> Callable:
    async def role_checker(current_user = Depends(get_current_active_user)):
        if current_user.role not in roles:
            raise HTTPException(403, f"Requires role: {', '.join(roles)}")
        return current_user
    return role_checker

# Usage:
@router.post("/products")
async def create_product(
    current_user = Depends(require_role("seller", "admin"))  # ← factory call
):
    ...
```

`require_role("seller", "admin")` is called at route registration time (not per-request).
It returns the `role_checker` async function, which FastAPI then calls for every request.
This is the **factory pattern**: a function that creates and returns another function.

---

### 2.4 JWT Authentication — Complete Flow

#### What is a JWT Token?

A JWT (JSON Web Token) is a base64url-encoded string in three parts: `header.payload.signature`

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9   ← header (base64url)
.
eyJzdWIiOiI1NTZhYjYxYy1mNWM5LTQwNWQi  ← payload (base64url)
.
dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFW ← signature (HMAC-SHA256)

Decoded payload:
{
    "sub": "556ab61c-f5c9-405d-...",   ← user's UUID ("subject")
    "role": "buyer",                   ← embedded, no DB query needed
    "exp": 1748123456,                 ← Unix timestamp, auto-checked by jose
    "type": "access"                   ← distinguishes from refresh token
}
```

The signature is `HMAC-SHA256(base64(header) + "." + base64(payload), SECRET_KEY)`.

**The server never stores tokens.** When a token arrives, we just verify the signature
matches. If someone modifies the payload (e.g., changes `"role": "buyer"` to `"role":
"admin"`), the signature check fails and the token is rejected.

#### Why Access Token (30 min) AND Refresh Token (7 days)?

| | Access Token | Refresh Token |
|--|--|--|
| TTL | 30 minutes | 7 days |
| Sent on | Every API request | Only to `/auth/refresh` |
| Stored in | `localStorage` | `localStorage` |
| If stolen | Usable for max 30 min | Can get new access tokens for 7 days |

Short access token TTL limits the damage if it's stolen (e.g., XSS attack). The refresh
token has a longer TTL so the user doesn't need to log in every 30 minutes. When the
access token expires, the Axios interceptor silently calls `/auth/refresh` with the
refresh token to get a new access token — transparent to the user.

In `backend/app/core/security.py`:
```python
def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["type"] = "access"
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
```

#### Login Flow — Code Trace

```
POST /api/v1/auth/login
Body: {"email": "amit@buyer.dev", "password": "Test1234!"}

backend/app/api/v1/auth.py → login()
  1. rate limiting check: redis.incr("login_attempts:{ip}") > 5 → 429
  2. get_user_by_email(db, "amit@buyer.dev") → User ORM object
  3. verify_password("Test1234!", user.hashed_password) → bcrypt.checkpw()
  4. redis.delete("login_attempts:{ip}")  ← reset counter on success
  5. create_access_token({"sub": str(user.id), "role": "buyer"})
  6. create_refresh_token({"sub": str(user.id), "role": "buyer"})
  7. return TokenResponse(access_token=..., refresh_token=..., token_type="bearer")
```

#### Protected Route Flow — Code Trace

```
GET /api/v1/auth/me
Headers: Authorization: Bearer eyJhbGciOiJIUzI1NiJ9...

FastAPI sees Depends(get_current_active_user)
  → calls get_current_user(oauth2_token=None, bearer_creds=HTTPAuthorizationCredentials(credentials="eyJ..."))
    → token = "eyJhbGciOiJIUzI1NiJ9..."
    → decode_token(token)
      → jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
      → verifies signature ✓
      → checks exp: 1748... > now ✓
      → returns {"sub": "556ab61c...", "role": "buyer", "type": "access"}
    → get_user_by_id(db, UUID("556ab61c..."))
      → SELECT * FROM users WHERE id = '556ab61c...' LIMIT 1
      → returns User ORM object
    → returns User

  → calls get_current_active_user(current_user=<User>)
    → checks user.is_active == True ✓
    → returns User

→ route function receives current_user = <User object>
→ returns UserResponse.model_validate(user)
```

---

### 2.5 SQLAlchemy 2.x — The Complete Explanation

#### What is an ORM and Why Use It?

An ORM (Object-Relational Mapper) lets you work with database rows as Python objects instead
of writing SQL strings. Compare:

```python
# Raw SQL (what ORM replaces):
result = await conn.execute(
    "SELECT id, email, full_name FROM users WHERE id = $1", [user_id]
)
row = result.fetchone()
user = {"id": row[0], "email": row[1], "full_name": row[2]}   # fragile

# ORM (what we actually write):
result = await db.execute(select(User).where(User.id == user_id))
user = result.scalar_one_or_none()  # User object with .email, .id, .full_name
```

Benefits: no SQL injection risk, Python type safety, relationships auto-loaded, schema
changes in one place, IDE autocomplete on `.email` etc.

#### Our Engine Config Explained

```python
# backend/app/core/database.py
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,    # Before using a connection, send "SELECT 1"
                           # If the DB restarted, the stale connection is discarded
                           # and a new one created. Prevents "connection closed" errors.
    pool_size=10,          # Keep 10 connections open permanently
                           # Why 10? At 512MB Render RAM, 10 connections × ~5MB each = 50MB
                           # Enough for concurrent requests without excessive memory
    max_overflow=20,       # Allow 20 MORE connections when pool is full
                           # Max total: 30. Under burst load, extra connections are created
                           # then closed after use (not returned to pool)
    echo=False,            # Don't log every SQL statement to console (too noisy in prod)
)
```

When all 10 pool connections are busy, the 11th request creates an "overflow" connection.
If you have 31+ simultaneous DB operations, the 31st blocks until one is released.

#### `mapped_column()` and `Mapped[T]`  — New vs Old Syntax

```python
# OLD SQLAlchemy 1.x syntax (Column):
class User(Base):
    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True)
    role = Column(String, default="buyer")
    # Problem: no type information, IDE can't know user.id is a UUID

# NEW SQLAlchemy 2.x syntax (mapped_column + Mapped):
class User(Base):
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    role: Mapped[str] = mapped_column(default="buyer")
    # Benefit: IDE knows user.id is uuid.UUID, user.email is str
    # mypy can check: user.email + 5  ← type error caught at development time
```

`Mapped[Optional[str]]` means the column is nullable (can be None). Without `Optional`,
the column is NOT NULL.

#### Relationships and Eager Loading

```python
# backend/app/models/user.py
class User(Base):
    products: Mapped[list["Product"]] = relationship(back_populates="seller")
    orders: Mapped[list["Order"]] = relationship(back_populates="buyer")
```

By default SQLAlchemy uses **lazy loading**: `user.products` triggers a NEW SQL query when
accessed. In an async context, lazy loading fails because it tries to open a sync DB
connection.

We use **eager loading** via `selectinload()`:

```python
# backend/app/crud/product.py
query = select(Product).options(
    selectinload(Product.seller),   # one extra query: SELECT * FROM users WHERE id IN (...)
    selectinload(Product.category), # one extra query for categories
    selectinload(Product.reviews),  # one extra query for reviews
)
```

`selectinload` emits one extra SQL query per relationship (not per row — it's `WHERE id IN
(1,2,3,...)` not one query per product). This avoids the N+1 query problem while staying
compatible with async.

#### Tracing a Complete DB Write: `create_user()`

```python
# backend/app/crud/user.py
async def create_user(db: AsyncSession, data: UserCreate, role: str = "buyer") -> User:
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),  # bcrypt hash computed HERE
        full_name=data.full_name,
        role=role,
    )
    db.add(user)        # adds object to session's "unit of work" — NO DB call yet
    await db.commit()   # flushes pending changes → INSERT INTO users (...) VALUES (...)
                        # → commits transaction (makes visible to other connections)
    await db.refresh(user)  # re-fetches the row from DB
                            # why? server-side defaults (created_at = now())
                            # aren't visible on the Python object until refresh
    return user
```

#### What is Alembic and Why Not `Base.metadata.create_all()`?

`Base.metadata.create_all(engine)` creates all tables that don't exist — but it
**never modifies existing tables**. If you add a column to `User`, `create_all()` silently
does nothing on an existing database.

Alembic solves this with migration scripts that describe incremental schema changes:

```
alembic revision --autogenerate -m "add phone to users"
```

Alembic compares your ORM models to the current DB schema and generates a migration file
with `op.add_column(...)`. Running `alembic upgrade head` applies it. This works on
production databases without data loss.

Our two migrations:
- `20260521_47f2dc0b571e_initial_schema.py` — creates all 6 tables
- `20260522_751b123db5f1_add_performance_indexes.py` — adds indexes for common queries

---

### 2.6 The SELECT FOR UPDATE Race Condition Fix

#### The Race Condition Bug

Without a lock, two buyers can simultaneously purchase the last item in stock:

```
Time 0: Product "Laptop" has stock=1
Time 1: Buyer A reads stock=1 → stock >= qty(1) ✓ → proceeds
Time 1: Buyer B reads stock=1 → stock >= qty(1) ✓ → proceeds (same millisecond!)
Time 2: Buyer A creates order, sets stock=0
Time 2: Buyer B creates order, sets stock=0  ← oversold! stock would be -1
Time 3: Both buyers have confirmed orders for 1 item
```

#### Our Fix in `backend/app/api/v1/orders.py`

```python
from sqlalchemy import select as sa_select
from app.models.product import Product as _Product

for item_req in data.items:
    result = await db.execute(
        sa_select(_Product)
        .where(_Product.id == item_req.product_id)
        .with_for_update()         # ← THIS LINE
    )
    locked_product = result.scalar_one_or_none()
    if locked_product:
        locked_product.stock -= item_req.quantity

await db.commit()                  # releases all locks
```

`with_for_update()` translates to `SELECT ... FOR UPDATE` in PostgreSQL. This acquires an
**exclusive row lock** on the product row. Any other transaction trying to SELECT FOR UPDATE
the same row will **block** until the first transaction commits.

```
Time 0: Product "Laptop" has stock=1
Time 1: Buyer A: SELECT * FROM products WHERE id=X FOR UPDATE → gets lock
Time 1: Buyer B: SELECT * FROM products WHERE id=X FOR UPDATE → BLOCKED (waiting)
Time 2: Buyer A: stock -= 1 → stock=0 → COMMIT → releases lock
Time 2: Buyer B: lock acquired → reads stock=0 → 0 >= 1? NO → 400 "Insufficient stock"
```

**What happens if payment fails after stock is decremented?**

The checkout endpoint decrements stock and creates the order before payment. If Razorpay's
payment fails, Razorpay sends a `payment.failed` webhook. The handler calls `cancel_order()`:

```python
# backend/app/crud/order.py
async def cancel_order(db: AsyncSession, order: Order) -> Order:
    from app.crud.product import update_product_stock
    order.status = "cancelled"
    await db.commit()
    for item in order.items:
        if item.product_id:
            await update_product_stock(db, item.product_id, delta=item.quantity)
            # delta=+1 → stock is restored
    return order
```

---

## SECTION 3: DATABASES & DATA LAYER

### 3.1 PostgreSQL — Our Primary Database

#### Why PostgreSQL over MySQL or SQLite?

| Feature | PostgreSQL | MySQL | SQLite |
|---------|-----------|-------|--------|
| JSON columns | Native JSONB | Limited | Limited |
| UUID native type | Yes | No (string) | No |
| FOR UPDATE locking | Yes | Yes | No |
| Concurrent writes | MVCC | MVCC | WAL (limited) |
| Supabase hosted | Yes | No | No |
| asyncpg driver | Yes | No | No |

SQLite is single-file, has no connection pooling, and can't handle concurrent writes from
multiple processes. Our Celery worker + FastAPI backend would corrupt it.

#### The 6 Tables and Their Relationships

```
users (1) ─────────────────────── (∞) products
   │  seller_id FK → users.id
   │
users (1) ─────────────────────── (∞) orders
   │  buyer_id FK → users.id
   │
products (1) ──────────────────── (∞) order_items
   │  product_id FK → products.id (SET NULL on delete — keeps order history)
   │
orders (1) ────────────────────── (∞) order_items
   │  order_id FK → orders.id (CASCADE — deleting order deletes its items)
   │
products (1) ──────────────────── (∞) reviews
   │  product_id FK → products.id (CASCADE)
   │
categories (1) ─────────────────── (∞) products
   │  category_id FK → categories.id (SET NULL — product survives category deletion)
   │
categories (1) ─────────────────── (∞) categories   ← self-referential
      parent_id FK → categories.id (SET NULL)
      Electronics → [Laptops, Phones, Tablets]
```

#### What `ondelete` Means

```python
# order_items.product_id:
ForeignKey("products.id", ondelete="SET NULL")
# When a product is deleted: order_item.product_id becomes NULL
# Why? The order history must survive product deletion.
# order_item.product_title is a snapshot — already stored as a string.

# order_items.order_id:
ForeignKey("orders.id", ondelete="CASCADE")
# When an order is deleted: all its items are automatically deleted
# Why? Order items have no meaning without their parent order.

# products.seller_id:
ForeignKey("users.id", ondelete="CASCADE")
# When a user is deleted: all their products are deleted too
# (In practice we soft-delete via is_active=False to avoid this)
```

#### The UniqueConstraint in Reviews

```python
# backend/app/models/review.py
__table_args__ = (
    UniqueConstraint("product_id", "user_id", name="uq_review_product_user"),
)
```

This creates a DB-level constraint: one review per (product_id, user_id) combination.
Even if our application code has a bug, PostgreSQL will reject the second INSERT with a
`UniqueViolationError`, which SQLAlchemy re-raises as an `IntegrityError`.
We catch this upstream and return `409 Conflict`.

#### JSON Columns for Images and Tags

```python
# backend/app/models/product.py
images: Mapped[list] = mapped_column(JSON, default=list)   # ["https://s3.../img1.jpg", ...]
tags: Mapped[list] = mapped_column(JSON, default=list)     # ["electronics", "laptop"]
metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
```

JSON columns store Python lists/dicts directly without needing junction tables.
For images and tags (bounded, small, not queried independently), this is simpler than
`product_images` and `product_tags` tables.

#### Why `Numeric(12, 2)` for Prices?

```python
price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
# Numeric(12, 2):
#   12 = total digits (precision)
#    2 = decimal places (scale)
# Max value: 9,999,999,999.99 (₹10 billion — enough for any product)
# Why not float? float(0.1) + float(0.2) = 0.30000000000000004 ← wrong for money!
# Decimal is exact arithmetic: Decimal("0.1") + Decimal("0.2") = Decimal("0.3")
```

---

### 3.2 Redis — Four Different Jobs in One Service

#### Job 1: Cart Storage (Hash Structure)

```
Redis Key:   cart:556ab61c-f5c9-405d-...    (user's UUID)
Type:        HASH
Structure:   field=product_uuid, value=quantity_string

Example:
  HGET  cart:556ab61c product_a_uuid → "2"
  HGET  cart:556ab61c product_b_uuid → "1"
  HGETALL cart:556ab61c → {"product_a": "2", "product_b": "1"}
```

**Why HASH instead of a LIST or JSON STRING?**

- `HSET cart:user product_id qty` — O(1), updates one item without rewriting the whole cart
- `HDEL cart:user product_id` — O(1), removes one item without rewriting
- `HGETALL cart:user` — O(N) where N is cart size, typically <20 items
- `HINCRBY cart:user product_id delta` — **atomic** increment (we cap at stock in Python, but the pattern exists)

With a JSON string: every update requires read → deserialize → modify → serialize → write.
Two concurrent "add to cart" calls for different products would require a compare-and-swap
loop. With HASH: concurrent writes to different fields are handled by Redis's single-threaded
command processing — no race condition.

**Why 30-day TTL?**

```python
CART_TTL = 60 * 60 * 24 * 30  # 2,592,000 seconds
await redis.expire(_cart_key(user_id), CART_TTL)
```

If a user abandons their cart, Redis automatically frees the memory after 30 days.
Without TTL, abandoned carts would accumulate indefinitely.

#### Job 2: Product and Category Cache

```
Key: products:slug:iphone-15-pro    TTL: 300s (5 min)
Key: products:list:a3f4e5d6...      TTL: 120s (2 min)  ← MD5 of query params
Key: categories:tree                TTL: 3600s (1 hour)
```

**How cache invalidation works:**

```python
# When a product is updated (products.py):
async def _invalidate_product_cache(slug: str) -> None:
    await cache_delete(f"products:slug:{slug}")       # delete specific product cache
    await cache_delete_pattern("products:list:*")     # delete ALL list caches
```

The pattern deletion (`SCAN + DEL`) is necessary because any listing with any filter params
might include this product. We accept the cost of re-warming many caches on update because
updates are rare compared to reads.

**Cache stampede**: if 1000 requests arrive simultaneously for an expired cache key, all
1000 miss and hit the database. Our code doesn't use a mutex/lock for this. For now,
the database can handle the burst. A production fix would use Redis `SET NX` (set if not
exists) to let only one request rebuild the cache while others wait.

#### Job 3: Celery Broker

```
When FastAPI calls send_order_confirmation_email.delay(order_id):
  → Celery serializes task to JSON
  → Redis LPUSH celery:default {"task": "...", "args": [order_id], ...}
  
When Celery worker runs:
  → Redis BRPOP celery:default 0  ← blocking pop, worker wakes when task arrives
  → Deserializes JSON
  → Calls send_order_confirmation_email(order_id)
```

Redis acts as a message queue (a list). `LPUSH` adds to the left, `BRPOP` blocks waiting
for items on the right. This is a simple FIFO queue. If the worker is offline, tasks
accumulate in Redis until it comes back.

#### Job 4: Login Rate Limiting

```python
# backend/app/api/v1/auth.py
rate_key = f"login_attempts:{client_ip}"
attempts = await redis.incr(rate_key)    # INCR is atomic — always returns new value
if attempts == 1:
    await redis.expire(rate_key, 60)     # set 60s TTL on first attempt
if attempts > 5:
    raise HTTPException(429, "Too many login attempts")
```

**How `INCR + EXPIRE` works:**
- `INCR login_attempts:1.2.3.4` → returns 1 (key created if not exists)
- `EXPIRE login_attempts:1.2.3.4 60` → set 60s TTL (only on first attempt)
- Next 4 attempts: INCR returns 2, 3, 4, 5 → allowed
- 6th attempt: INCR returns 6 → 429

After 60 seconds: Redis automatically deletes the key. Counter resets.

**Why per-IP not per-email?** An attacker trying to lock out a specific user's account
would target one email from many IPs. Per-email limiting would be trivially bypassed by
changing IPs, while making brute-force harder. Per-IP limits brute-force attempts while
not allowing targeted account lockout.

---

### 3.3 Elasticsearch — Why It Exists Alongside PostgreSQL

#### What Elasticsearch Can Do That PostgreSQL `ILIKE` Cannot

```sql
-- PostgreSQL ILIKE:
SELECT * FROM products WHERE title ILIKE '%laptop%';
-- Problems:
-- 1. Can't use index — full table scan every time
-- 2. No relevance scoring — "Laptop Stand" ranks same as "Gaming Laptop"
-- 3. No typo tolerance — "laptap" returns nothing
-- 4. No multi-field search — title OR description requires UNION

-- Elasticsearch equivalent:
{
  "query": {
    "multi_match": {
      "query": "laptop",
      "fields": ["title^3", "tags^2", "description"],
      "fuzziness": "AUTO"   ← "laptap" still finds "laptop"
    }
  }
}
-- Results ordered by relevance score (BM25)
-- "Gaming Laptop Pro" scores higher than "Laptop Stand" if "gaming" is also in query
```

#### What is an Inverted Index?

A normal index answers: "What's on row 5?" An inverted index answers: "Which rows contain
the word 'laptop'?"

```
Forward (normal):
  product 1 → "Gaming Laptop Pro"
  product 2 → "Laptop Stand for Desk"

Inverted:
  "gaming"  → [product 1]
  "laptop"  → [product 1, product 2]
  "pro"     → [product 1]
  "stand"   → [product 2]
  "desk"    → [product 2]
```

A search for "laptop" does one O(1) lookup in the inverted index → returns [1, 2].
No sequential scan needed.

#### Our Index Mapping

```python
# backend/app/services/search.py
mappings = {
    "properties": {
        "title":    {"type": "text",    "analyzer": "standard"},
        # "text": tokenized, analyzed, searchable (split into words, lowercased)
        "description": {"type": "text", "analyzer": "standard"},
        "tags":     {"type": "keyword"},
        # "keyword": exact match only — "electronics" != "Electronics"
        # Better for filtering: WHERE tags = "electronics"
        "price":    {"type": "double"},
        "stock":    {"type": "integer"},
        "status":   {"type": "keyword"},  # always exact: "active" / "draft"
        "rating":   {"type": "float"},
    }
}
```

#### Field Boosting in Our Search

```python
# backend/app/services/search.py
"multi_match": {
    "query": q,
    "fields": ["title^3", "description", "tags^2"],
}
```

`^3` means title matches multiply the relevance score by 3. If a product's title contains
the exact search term, it ranks 3× higher than products where only the description matches.
Tags boost by 2×. This produces intuitive results: a product named "Laptop" ranks above
one whose description merely mentions laptops.

BM25 (Best Match 25) is the default scoring algorithm — it rewards terms that appear
frequently in a document but are rare across all documents (like TF-IDF with improvements).

#### How We Keep ES in Sync with PostgreSQL

When a product is created or updated:
```python
# backend/app/api/v1/products.py
product = await create_product(db, schema, ...)   # write to PostgreSQL
await _reindex(product)                           # write to Elasticsearch
```

`_reindex()` calls `ElasticsearchService.index_product()` which sends a PUT request to ES.

This is **dual-write** — we write to both stores. The risk: if ES write fails after PG
write succeeds, ES is stale. Our code wraps the ES call in `try/except pass` — ES failure
is non-fatal. A product might be temporarily absent from search but still accessible via
direct URL. This trade-off accepts occasional inconsistency to avoid complex distributed
transaction handling.

#### The 512MB Heap Limit

```yaml
# docker-compose.yml
environment:
  - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
  # Xms = initial heap size, Xmx = max heap size (both same = no GC pauses)
mem_limit: 1g    # Docker hard limit on the container's total RAM
```

Elasticsearch defaults to using 50% of available RAM for its heap. On an 8GB machine that
would be 4GB just for ES — leaving nothing for PostgreSQL, Redis, the backend, and Celery.
512MB heap + 512MB OS overhead (file system cache, JVM non-heap) = ~1GB total. Safe.

---

## SECTION 4: PAYMENT SYSTEM — RAZORPAY COMPLETE FLOW

### Sequence Diagram

```
Browser                  FastAPI                 PostgreSQL           Razorpay API
   │                        │                        │                     │
   │── POST /checkout ──────►│                        │                     │
   │                        │── SELECT products ────►│                     │
   │                        │◄── product data ────────│                     │
   │                        │                        │                     │
   │                        │  calculate: subtotal + GST 18% + shipping   │
   │                        │  amount_paise = int(total × 100)            │
   │                        │                        │                     │
   │                        │── create_order() ──────────────────────────►│
   │                        │◄── {id: "order_xxx", amount, currency} ──────│
   │                        │                        │                     │
   │                        │── SELECT FOR UPDATE ──►│                     │
   │                        │── UPDATE stock ────────►│                     │
   │                        │── INSERT Order ─────────►│                     │
   │                        │── DELETE cart (Redis) ──│                     │
   │                        │                        │                     │
   │◄── CheckoutResponse ───│                        │                     │
   │  {razorpay_order_id,    │                        │                     │
   │   amount, key_id}       │                        │                     │
   │                        │                        │                     │
   │─── opens Razorpay modal ─────────────────────────────────────────────►│
   │                        │                        │   User pays UPI     │
   │                        │                        │                     │
   │                        │◄────────── POST /webhook ────────────────────│
   │                        │   X-Razorpay-Signature: <hmac>               │
   │                        │                        │                     │
   │                        │  verify_webhook_signature(body, sig) ✓       │
   │                        │                        │                     │
   │                        │── SELECT Order ────────►│                     │
   │                        │◄── Order{status=pending}│                     │
   │                        │                        │                     │
   │                        │  check order.status == "pending" (idempotency)│
   │                        │                        │                     │
   │                        │── UPDATE status=paid ──►│                     │
   │                        │── WS notify buyer       │                     │
   │                        │── WS notify sellers     │                     │
   │                        │── email_task.delay()    │                     │
   │                        │                        │                     │
   │                        │──── {"status": "ok"} ───────────────────────►│
```

### Key Concepts Explained

#### What is Paise?

`1 INR = 100 paise`. Razorpay requires amounts as integers in paise to avoid floating-point
arithmetic. `₹299.99 → 29999 paise`. An order for ₹1,234.56 is sent as `amount: 123456`.

#### What is `payment_capture: 1`?

```python
# backend/app/services/razorpay.py
return client.order.create({
    "amount": amount_paise,
    "currency": "INR",
    "receipt": receipt,
    "payment_capture": 1,   ← auto-capture
})
```

`payment_capture: 1` means Razorpay automatically captures (settles) the payment the moment
the user pays. The alternative (manual capture) is for businesses that want to authorize
payment now but only charge the card when shipping — not needed for our digital platform.

#### What is Webhook Signature Verification?

```python
# backend/app/services/razorpay.py
def verify_webhook_signature(body: bytes, signature: str) -> bool:
    client = get_razorpay_client()
    try:
        client.utility.verify_webhook_signature(
            body.decode(),      # raw request body as string
            signature,          # value of X-Razorpay-Signature header
            settings.RAZORPAY_KEY_SECRET
        )
        return True
    except Exception:
        return False
```

Razorpay computes `HMAC-SHA256(raw_body, key_secret)` and puts it in the
`X-Razorpay-Signature` header. We recompute the same HMAC with the same key and compare.
If they match, the webhook is genuinely from Razorpay (only they know the key_secret).

**What happens without verification?** Any attacker could POST to `/orders/webhook` with
`{"event": "payment.captured", "payload": {"payment": {"entity": {"order_id": "xxx"}}}}` 
and mark any order as paid without actual payment.

#### What is Idempotency?

Razorpay can fire the same webhook multiple times (network retry on timeout, infrastructure
issues). Our guard:

```python
if event == "payment.captured" and order.status == "pending":
    # Only process if STILL pending — already processed → order.status is "paid"
    await update_order_status(...)
```

If the webhook fires twice for the same payment, the second time `order.status == "paid"` 
(not `"pending"`), so the condition is False — we do nothing. This is idempotency: the
same operation can be applied multiple times with the same result.

---

## SECTION 5: BACKGROUND TASKS — CELERY + RESEND

### 5.1 Why Celery (Not Inline Code)?

```
Without Celery (inline email):
  POST /orders/webhook arrives at 0ms
  verify signature: 2ms
  update DB: 15ms
  call Resend API: 250ms  ← user's request is blocked for 250ms
  return {"status": "ok"} at 267ms

With Celery:
  POST /orders/webhook arrives at 0ms
  verify signature: 2ms
  update DB: 15ms
  redis.lpush(task_data): 1ms  ← queue the task, don't execute it
  return {"status": "ok"} at 18ms   ← Razorpay marked delivered

  [250ms later, in the Celery worker]
  Celery picks up task, calls Resend API, email sent
```

Razorpay has a webhook response timeout. Returning quickly ensures no false "failed webhook"
retries.

### 5.2 Our Celery Configuration

```python
# backend/app/tasks/celery_app.py
celery_app = Celery(
    "marketplace",
    broker=settings.REDIS_URL,   # where tasks are published and consumed
    backend=settings.REDIS_URL,  # where task results are stored (for tracking)
    include=["app.tasks.email_tasks", "app.tasks.image_tasks"],
)
celery_app.conf.update(
    task_serializer="json",      # serialize tasks as JSON (not pickle — safer)
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",     # IST — important for scheduled tasks
    enable_utc=True,
    worker_concurrency=2,        # 2 worker threads — conservative for 8GB RAM
)
```

**Why JSON not pickle?** Pickle can execute arbitrary Python code when deserialized — a
security risk if the Redis broker is shared or compromised. JSON is safe: it can only
represent data, not code.

**Why concurrency=2?** Each Celery thread is a Python process (prefork model). Each needs
its own DB connection pool, Redis connection, and memory. On 8GB RAM with ES, Redis, PG,
and FastAPI all running, 2 workers is the safe ceiling.

#### `bind=True` and `self.retry()`

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_confirmation_email(self, order_id: str):
    # bind=True means the task function receives "self" as the first argument
    # self is the Task instance — gives access to retry(), request, etc.
    try:
        resend.Emails.send({...})
    except Exception as exc:
        raise self.retry(exc=exc)
        # self.retry() raises a special Retry exception
        # Celery catches it, waits 60s, tries again
        # After max_retries=3 failures, raises MaxRetriesExceededError
```

### 5.3 asyncio Inside Celery Tasks

The Celery email tasks use `asyncio.run()` with our async SQLAlchemy session. This works
because Celery workers are synchronous by default (no running event loop), and
`asyncio.run()` creates a brand new event loop, runs the coroutine to completion, and
closes the loop.

```python
# backend/app/tasks/email_tasks.py
async def _fetch():
    async with AsyncSessionLocal() as db:   # async session — same as FastAPI
        order = await get_order(db, order_id)
        user = await get_user_by_id(db, order.buyer_id)
        return order, user

order, user = asyncio.run(_fetch())   # ONE asyncio.run() per task
# ↑ this blocks the Celery thread until the coroutine finishes
# That's OK: Celery workers are synchronous threads, blocking is expected
```

**CRITICAL**: `asyncio.run()` can only be called once per thread (it errors if an event
loop is already running). This is why ALL database fetching happens in a single `_fetch()`
coroutine, not multiple `asyncio.run()` calls.

### 5.4 Resend vs SMTP

```
SMTP approach (painful):
  1. Need an SMTP server (localhost:25, AWS SES, SendGrid)
  2. Configure TLS, authentication, DKIM, SPF, DMARC
  3. Handle connection pooling, retries, bounces
  4. Python: smtplib.SMTP_SSL("smtp.sendgrid.net", 465, ...) — many lines of setup

Resend approach (our code):
  resend.api_key = settings.RESEND_API_KEY
  resend.Emails.send({
      "from": "onboarding@resend.dev",   ← sandbox sender, works without domain setup
      "to": [recipient],
      "subject": "...",
      "html": "..."
  })
```

One function call. No connection management. Resend handles deliverability, bounces, and
unsubscribes through their API.

`onboarding@resend.dev` is Resend's sandbox sender — available for testing without
verifying a custom domain. In production, you'd verify `noreply@yourdomain.com`.

**The TEST_EMAIL_OVERRIDE pattern:**
```python
recipient = settings.TEST_EMAIL_OVERRIDE or user.email
```

In Resend's free test mode, emails only deliver to the account owner's address. We redirect
all emails to `gautamkumarnita@gmail.com` during development so we receive them without
needing to verify a domain.

---

## SECTION 6: FRONTEND ARCHITECTURE

### 6.1 React 19 + Vite — Why Not Create React App?

| | Create React App | Vite |
|--|--|--|
| Dev server start | ~30 seconds | <1 second |
| Hot reload | Re-bundles changed module | Replaces only changed module (HMR) |
| Build speed | ~60 seconds | ~10 seconds |
| Config | Ejected webpack | Simple `vite.config.ts` |
| Status | Deprecated (no updates) | Actively maintained |

**Why the difference?** Vite uses native ES modules in development — the browser imports
files directly without bundling. Only changed files are invalidated. Webpack (CRA) bundles
everything into one file and rebuilds the bundle on every change.

**What is the build output?** `npm run build` produces `frontend/dist/`:
```
dist/
  index.html
  assets/
    index-a3f4e5d6.js   ← all your code + React + libraries, minified
    index-b2c3d4e5.css  ← all CSS, minified
```

This is a **static site** — no server needed. Vercel serves these files from a CDN.
When a user navigates to `/orders/123`, Vercel serves `index.html` (SPA fallback), and
React Router handles the `/orders/123` route on the client side.

### 6.2 Zustand vs Redux

Our three stores:

```typescript
// authStore.ts — who is the user?
{
    user: User | null          // full user object (from /auth/me)
    isAuthenticated: boolean   // true when logged in
    setAuth(user, tokens)      // called after login: stores tokens in localStorage
    logout()                   // removes tokens from localStorage
}

// cartStore.ts — client-side cart count
{
    cart: CartResponse | null  // current cart (from React Query)
    setCart(cart)
    clearCart()
}

// notificationStore.ts — real-time notification bell
{
    notifications: WsNotification[]   // last 50 WebSocket events
    unreadCount: number
    addNotification(n)
    markAllRead()
    clear()                    // called on logout
}
```

**Why Zustand over Redux?**

```typescript
// Redux requires:
// 1. Action types:     const SET_USER = "auth/SET_USER"
// 2. Action creators:  const setUser = (user) => ({type: SET_USER, payload: user})
// 3. Reducer:          case SET_USER: return {...state, user: action.payload}
// 4. Dispatch:         dispatch(setUser(user))  — in component

// Zustand:
const logout = useAuthStore(s => s.logout)
logout()   // direct call, no dispatch, no boilerplate
```

**What is localStorage persistence in authStore?**

```typescript
// authStore.ts
export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({...}),
        {
            name: "auth-store",   // localStorage key
            partialize: (state) => ({
                user: state.user,
                isAuthenticated: state.isAuthenticated
                // tokens are in localStorage.access_token separately
            }),
        }
    )
)
```

`persist` middleware serializes `{user, isAuthenticated}` to `localStorage["auth-store"]`.
When the page refreshes, Zustand reads this back — the user is still logged in without
a server call. The actual JWT is stored separately in `localStorage.access_token`.

### 6.3 React Query — Server State Management

**The problem it solves:**

```typescript
// Without React Query — manual state management:
const [products, setProducts] = useState([])
const [loading, setLoading] = useState(false)
const [error, setError] = useState(null)

useEffect(() => {
    setLoading(true)
    fetch("/api/v1/products")
        .then(r => r.json())
        .then(data => { setProducts(data.items); setLoading(false) })
        .catch(err => { setError(err); setLoading(false) })
}, [])
// Also: no caching, no background refresh, refetch on every mount

// With React Query:
const { data, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts()
})
// Automatic caching, background refetch, loading/error states, no useEffect
```

**Server state vs client state:**
- `authStore` (Zustand) = client state: "Am I logged in?" — no server needed
- `useOrders()` (React Query) = server state: "What are my orders?" — fetched from server

**Query invalidation:**

```typescript
// frontend/src/hooks/useWebSocket.ts
ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    queryClient.invalidateQueries({ queryKey: ['orders'] })      // list stale
    queryClient.invalidateQueries({ queryKey: ['order', msg.order_id] })  // detail stale
}
```

When a WebSocket event arrives (order status changed), we invalidate the React Query cache.
React Query refetches in the background, and the UI updates automatically — no page reload.

### 6.4 Axios Interceptors — The Complete Auth Flow

```typescript
// frontend/src/api/client.ts

// REQUEST interceptor — runs before every API call
apiClient.interceptors.request.use((config) => {
    const token = localStorage.getItem("access_token")
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// RESPONSE interceptor — runs when 401 is received
apiClient.interceptors.response.use(
    (response) => response,    // success: pass through
    async (error) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true   // prevent infinite retry loop
            isRefreshing = true

            const refreshToken = localStorage.getItem("refresh_token")
            if (!refreshToken) {
                _logout()   // no refresh token → force login
                return Promise.reject(error)
            }

            try {
                const { data } = await axios.post("/api/v1/auth/refresh", {
                    refresh_token: refreshToken
                })
                localStorage.setItem("access_token", data.access_token)
                localStorage.setItem("refresh_token", data.refresh_token)
                originalRequest.headers.Authorization = `Bearer ${data.access_token}`
                return apiClient(originalRequest)   // retry original request with new token
            } catch {
                _logout()
                return Promise.reject(error)
            }
        }
    }
)
```

Without this interceptor, every component that makes API calls would need to handle 401,
call /refresh, and retry. With the interceptor: components never see a 401. The token
refresh is transparent.

### 6.5 TypeScript — Why It Mirrors Backend Schemas

```typescript
// frontend/src/types/index.ts
export interface CheckoutResponse {
    order_id: string            // matches Python: order_id: uuid.UUID → str
    razorpay_order_id: string   // matches Python: razorpay_order_id: str
    amount: number              // matches Python: amount: int (paise)
    currency: string            // matches Python: currency: str = "INR"
    razorpay_key_id: string     // matches Python: razorpay_key_id: str
}
```

If the backend changes `amount` from `int` to `str`, TypeScript's compiler would show
an error in every place `amount` is used as a number. Without TypeScript, this would
be a runtime bug that only appears in the browser.

**Real example caught by TypeScript:**
A backend returns `Decimal` for prices. Pydantic serializes `Decimal` to JSON strings.
Without TypeScript: `"299.00" + 100 = "299.00100"` (string concatenation, not addition).
With TypeScript: `number + number` compiles. `string + number` fails. The `Number()` 
conversion is enforced by the type system.

---

## SECTION 7: INFRASTRUCTURE & DEVOPS

### 7.1 Docker Compose — Service by Service

```yaml
# docker-compose.yml — full breakdown

postgres:
    image: postgres:16-alpine   # alpine = smaller image (~100MB vs ~400MB)
    environment:
        POSTGRES_DB: marketplace
        POSTGRES_USER: marketplace
        POSTGRES_PASSWORD: marketplace
    healthcheck:
        test: ["CMD-SHELL", "pg_isready -U marketplace"]
        interval: 10s
        timeout: 5s
        retries: 5
    # healthcheck ensures other services don't start until PG is accepting connections
    # without this: backend starts, tries to connect, PG isn't ready → crash
```

```yaml
redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    # --appendonly yes = AOF persistence
    # Every write command is appended to appendonly.aof
    # On restart: Redis replays the log to restore state
    # Without this: Redis starts empty after every docker compose restart
    # (cart data, cache, rate limits all lost)
```

```yaml
elasticsearch:
    image: elasticsearch:8.12.0
    environment:
        - "ES_JAVA_OPTS=-Xms512m -Xmx512m"   # heap: 512MB min and max
        - "discovery.type=single-node"         # no cluster coordination overhead
        - "xpack.security.enabled=false"       # no SSL/auth for dev (simpler)
        - "cluster.routing.allocation.disk.threshold_enabled=false"
        # ↑ Without this: ES refuses to index if disk is >85% full
        #   In dev on a laptop, disk can be over 85% → ES enters read-only mode
    mem_limit: 1g                              # Docker hard limit — critical on 8GB machine
```

```yaml
backend:
    environment:
        - REDIS_URL=redis://redis:6379/0         ← container hostname, not localhost!
        - DATABASE_URL=postgresql+asyncpg://...@postgres:5432/...
        - ELASTICSEARCH_URL=http://elasticsearch:9200
    # env_file: .env loads the dev .env which has localhost URLs
    # the environment: block OVERRIDES those with container service names
    # This is the critical fix for the "Celery uses localhost" bug
```

#### Docker Networking — Why Containers Use Service Names

Inside a Docker Compose network, each service gets a DNS hostname equal to its service
name. `redis` resolves to the Redis container's internal IP. `localhost` inside the backend
container refers to the backend container itself — not your host machine.

```
Host machine:
  localhost:6379 → Redis (via port mapping)
  
Inside backend container:
  localhost:6379 → NOTHING (no Redis process in backend container)
  redis:6379     → Redis container ✓
```

This was a real bug hit during development. The `.env` file had `REDIS_URL=redis://localhost:6379`
(correct for direct development). When running via Docker Compose, the backend container
tried to connect to `localhost:6379` — its own empty container. The `environment:` override
in `docker-compose.yml` with `redis://redis:6379` fixes this.

### 7.2 GitHub Actions CI/CD

```yaml
# .github/workflows/ci.yml breakdown

backend-test:
    services:
        postgres:           ← a fresh PG container, only for this job
            image: postgres:16-alpine
            env:
                POSTGRES_DB: marketplace_test   ← test DB, not dev DB
        redis:
            image: redis:7-alpine
    steps:
        - pip install -r backend/requirements.txt
        - pytest tests/ -q --tb=short --cov=app --cov-report=term-missing
    env:
        USE_LOCAL_STORAGE: "true"   ← skips S3 calls in tests
        RAZORPAY_KEY_ID: rzp_test_fake   ← fake keys (Razorpay is mocked in tests)
```

**Service containers in GitHub Actions**: Spin up real Docker containers (not mocks)
as sidecar services for the test job. Tests run against a real PostgreSQL and Redis.
This catches bugs that in-memory fakes would miss.

**Why a fresh test DB?** Our `conftest.py` creates tables at session start and drops them
at the end. Using the dev DB would corrupt it. Using a separate `marketplace_test` DB
keeps dev data intact and allows parallel CI runs.

```yaml
backend-lint:
    steps:
        - pip install ruff
        - ruff check backend/app --select E,W,F --ignore E501
    # E = PEP8 errors, W = warnings, F = pyflakes (unused imports, undefined names)
    # ignore E501 = don't enforce line length (we use 120 in pyproject.toml)
    # F401 = unused import — would catch leftover imports from refactoring

frontend-build:
    steps:
        - npm ci              ← clean install (uses package-lock.json exactly)
        - npx tsc --noEmit    ← type check only, no output
        - npm run build       ← full Vite production build
    # This caught a real bug: unused TypeScript variable STATUS_ORDER
    # tsc --noEmit verifies types, npm run build verifies no import errors
```

### 7.3 AWS S3 Image Upload Flow

```
1. Seller selects image file on CreateProductPage
2. Frontend reads file, validates locally (type + size)
3. POST /api/v1/products (multipart/form-data, images=[file])

4. backend/app/api/v1/products.py → create_new_product()
   for img_file in images:
       content = await img_file.read()         # read bytes
       if len(content) > 5MB: raise 400        # check size BEFORE S3
       await img_file.seek(0)                  # reset file pointer for upload
   url = await upload_image(img_file, folder="products")

5. backend/app/services/storage.py → upload_image()
   data = await file.read()
   img = Image.open(io.BytesIO(data))          # Pillow opens the image
   if img.width > 1200 or img.height > 1200:
       img.thumbnail((1200, 1200), Image.LANCZOS)  # resize to max 1200px
   buffer = io.BytesIO()
   img.save(buffer, format="JPEG", quality=85) # convert to JPEG, compress
   key = f"products/{uuid.uuid4()}.jpg"        # unique filename
   s3 = get_s3_client()
   s3.put_object(
       Bucket=settings.S3_BUCKET_NAME,
       Key=key,
       Body=buffer.getvalue(),
       ContentType="image/jpeg",
       ACL="public-read"                       # anyone can read this URL
   )
   return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"

6. URL returned, stored in product.images JSON column
```

**What is IAM?** AWS Identity and Access Management. Instead of using root account
credentials, we create a dedicated `marketplace-s3-user` with only S3 permissions.
If this key leaks, an attacker can only access S3 — not EC2, RDS, etc.

**ACL=public-read vs pre-signed URLs:**
- `public-read`: the S3 URL is public, anyone with the URL can view the image.
  Suitable for product images — we want them publicly accessible.
- Pre-signed URL: a time-limited URL with an embedded signature. Used for private files
  (user documents, invoices). Not needed for product images.

---

## SECTION 8: SECURITY — EVERY MEASURE EXPLAINED

### 8.1 bcrypt Password Hashing

**What would happen without it:** If our database is breached, attackers get `hashed_password`
strings. Without hashing, these would be plaintext passwords. With bcrypt, they're useless
without the original password.

**Rainbow table attack:** Attackers precompute hashes of every common password
(`md5("password") = 5f4dcc3b5aa765d61d8327deb882cf99`). Given the hash, they look up
the original. bcrypt prevents this with:

1. **Salt:** A random 22-character string generated per-password and stored in the hash.
   `bcrypt("password", salt1)` ≠ `bcrypt("password", salt2)`. Rainbow tables are useless.

2. **Work factor (cost):** bcrypt runs the hashing algorithm N times (N = 2^cost, typically
   2^12 = 4096). Makes brute-force 4096× slower. The cost is embedded in the hash and
   can be increased as hardware improves.

```python
# backend/app/core/security.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hash_password("Test1234!") → "$2b$12$randomsalt22chars...hashedresult"
                                   ↑  ↑
                               cost=12  salt embedded in hash
```

**Why `bcrypt<4.0.0`?** bcrypt 4.0.0 changed its Python C extension ABI in a way that
breaks passlib's wrapper. This is pinned in `requirements.txt` until passlib releases
a compatible update.

### 8.2 JWT Token Security

**Token forgery:** If `SECRET_KEY` is secret, an attacker can't forge a valid token.
They could modify the payload (change `"role":"buyer"` to `"role":"admin"`) but then
the signature verification fails — the signature was computed on the original payload.

**Token replay attack:** A stolen access token can be used until it expires (30 min).
Unlike session tokens (server can revoke them), JWTs are stateless — we can't invalidate
a single token. Short TTL (30 min) limits the damage window.

**If someone steals a refresh token:** They can get new access tokens for 7 days. This is
more damaging. Mitigations (not yet implemented): refresh token rotation (invalidate old
refresh token after each use), device-specific refresh tokens, revocation via DB lookup.

### 8.3 Razorpay Webhook Signature Verification

**HMAC-SHA256 explained:**
```
HMAC(message, key) = SHA256(key XOR opad + SHA256(key XOR ipad + message))
                             ↑ this nested construction prevents length extension attacks
```

Razorpay sends: `X-Razorpay-Signature: HMAC-SHA256(request_body, RAZORPAY_KEY_SECRET)`

We compute: `HMAC-SHA256(request_body, our_RAZORPAY_KEY_SECRET)` and compare.

If they match: the message was created by someone who knows `RAZORPAY_KEY_SECRET` — only
Razorpay. An attacker sending a fake webhook won't know the key secret and can't produce
a matching signature.

**IMPORTANT:** We call `await request.body()` to get raw bytes BEFORE `json.loads()`.
Parsing modifies whitespace. The signature was computed on the exact bytes Razorpay sent.

### 8.4 Login Rate Limiting

```python
# 5 attempts per 60 seconds per IP
rate_key = f"login_attempts:{client_ip}"
attempts = await redis.incr(rate_key)
if attempts == 1: await redis.expire(rate_key, 60)
if attempts > 5: raise HTTPException(429, "Too many login attempts")
```

**Brute force attack:** Try every password combination automatically.
`english dictionary = ~170k words × 10 variations = 1.7M attempts`
At 1000 req/s without limiting: cracked in seconds.
With 5/60s limit: 1.7M attempts × 12 seconds/attempt = 5.7 years.

### 8.5 SELECT FOR UPDATE (Race Condition)

Covered fully in Section 2.6. The key point: the lock is held for microseconds during
the stock decrement, not for the entire order creation process. Low contention cost,
high protection value.

### 8.6 SQL Injection Prevention

```python
# DANGEROUS — raw SQL (we never do this):
user_input = "'; DROP TABLE products; --"
await db.execute(f"SELECT * FROM products WHERE title = '{user_input}'")
# Executes: SELECT * FROM products WHERE title = ''; DROP TABLE products; --'

# SAFE — SQLAlchemy ORM (what we always do):
await db.execute(select(Product).where(Product.title == user_input))
# Generates: SELECT * FROM products WHERE title = $1
# PostgreSQL treats $1 as a literal string, can't execute as SQL
```

SQLAlchemy uses parameterized queries (prepared statements). User input is always a
parameter value — never interpreted as SQL syntax.

### 8.7 CORS Configuration

```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),  # ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**What CORS is:** Browsers refuse to make cross-origin API calls unless the server
explicitly permits it. `allow_origins=["http://localhost:5173"]` says: "Only the React
dev server can make requests to this API from a browser."

**What `*` would mean:** Any website in any browser could make authenticated API calls.
An attacker's `evil.com` could read the victim's cart, orders, or profile if the victim
visits `evil.com` while logged in.

**Why credentials=True matters:** Allows cookies to be sent cross-origin. Combined with
non-wildcard origins, this is safe.

### 8.8 Pydantic Input Validation

```python
# ShippingAddress (schemas/order.py):
@field_validator("pincode")
@classmethod
def validate_pincode(cls, v: str) -> str:
    if not v.isdigit() or len(v) != 6:
        raise ValueError("Pincode must be exactly 6 digits")
    return v
# Prevents: "abc" / "123456789" / "<script>" — all rejected before DB write

# ReviewCreate (schemas/review.py):
@field_validator("rating")
@classmethod
def rating_range(cls, v: int) -> int:
    if not 1 <= v <= 5:
        raise ValueError("Rating must be between 1 and 5")
    return v
# Without this, a 0 or -1 rating could corrupt average calculations

# UserCreate (schemas/user.py):
@field_validator("password")
@classmethod
def password_min_length(cls, v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    return v
```

Any validation failure produces a `422 Unprocessable Entity` with a structured JSON body
explaining exactly which field failed and why. The route function never runs.

---

## SECTION 9: TESTING — HOW OUR 108 TESTS WORK

### 9.1 Why Async Tests Are Hard

```python
# Synchronous test — simple:
def test_add():
    assert 1 + 1 == 2

# Async test — needs an event loop to run:
async def test_create_user():
    result = await create_user(db, data)   # can't call this without an event loop
    assert result.email == "a@b.com"
```

Standard pytest doesn't run event loops. `pytest-asyncio` provides one.

```ini
# pytest.ini
asyncio_mode = auto           # mark ALL async test functions automatically
pythonpath = . backend        # makes "from app.xxx import" work from project root
```

**Why `pythonpath = . backend`?** Tests live in `C:\Projects\marketplace\tests\` and
import `from app.core.security import ...`. Adding `backend` to pythonpath means Python
looks in `backend/` for modules, so `backend/app/` is found as `app/`.

### 9.2 The conftest.py Fixtures — Fully Explained

```python
# tests/conftest.py

# Why session scope for event_loop?
# pytest-asyncio creates one event loop per session by default.
# All async tests share it. This avoids "event loop closed" errors when
# one async fixture creates DB tables that another test uses.
@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Creates all tables ONCE for the test session.
# scope="session" means this runs once, not per test.
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)    # creates empty tables
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)      # cleanup after all tests

# autouse=True = runs for EVERY test automatically, no need to include in params
@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield   # test runs here
    # AFTER test: truncate all tables + flush Redis
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {all_tables} RESTART IDENTITY CASCADE"))
    # This gives test isolation: each test starts with an empty database

# The async_client fixture is the most important:
@pytest_asyncio.fixture
async def async_client():
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session       # TestSessionLocal uses the TEST DB

    app.dependency_overrides[get_db] = override_get_db
    # ↑ Override FastAPI's get_db() to use TEST DB instead of dev DB
    # Every route that calls Depends(get_db) now gets a test session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()   # reset after test

# Pre-built tokens — most tests just need "a valid buyer JWT", not a real user
@pytest_asyncio.fixture
async def buyer_token(buyer_user: User) -> str:
    return create_access_token({"sub": str(buyer_user.id), "role": buyer_user.role})
```

### 9.3 Test Anatomy — A Complete Walkthrough

Let's trace `test_ws_connect_valid_token` from `tests/test_websocket.py`:

```python
def test_ws_connect_valid_token():
    # Note: sync function (not async) — WebSocket tests use Starlette's sync TestClient
    token = _make_token()              # creates a JWT with a random user_id UUID
    with TestClient(app) as client:    # starts the ASGI app in a test thread
        with client.websocket_connect(f"/api/v1/ws?token={token}") as ws:
            ws.send_text("ping")       # sends keep-alive message
            # If no exception raised: connection was accepted successfully ✓
```

And `test_ws_connect_invalid_token`:
```python
def test_ws_connect_invalid_token():
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws?token=not.a.real.token") as ws:
            with pytest.raises(Exception):
                ws.receive_text()      # server closes connection with code 4008
                # Starlette raises WebSocketDisconnect when server closes
```

The WebSocket tests use Starlette's synchronous `TestClient`, not `httpx.AsyncClient`,
because WebSocket test infrastructure requires synchronous context managers.

### 9.4 What 108 Tests Cover

| File | Tests cover |
|------|-------------|
| `test_auth.py` | register, login, rate limiting, refresh token, /me, inactive user |
| `test_products.py` | CRUD, ownership (buyer can't create), image upload, 5MB limit, slug uniqueness |
| `test_orders.py` | checkout, stock validation, webhook flow, cancel, insufficient stock |
| `test_cart.py` | add item, update quantity, remove item, own product guard, stale cleanup |
| `test_categories.py` | tree listing, create, update, delete, active product guard |
| `test_reviews.py` | create, update, delete, helpful votes, duplicate guard, role guard |
| `test_admin.py` | user management, product moderation, stats, review deletion |
| `test_order_status.py` | all valid transitions, invalid transition rejection, seller ownership |
| `test_websocket.py` | valid token connects, invalid token rejected (4008), missing token |

**What's NOT tested:**
- Actual Razorpay API calls (mocked with fake keys that pass format validation)
- Actual Resend email delivery (email tasks run but Resend API is not called in tests)
- S3 uploads (`USE_LOCAL_STORAGE=true` in CI)
- Elasticsearch search (ES not running in CI — tests fall back to DB)
- WebSocket message delivery to specific users (only connection is tested)
- Rate limiting window behavior (would require time manipulation)

---

## SECTION 10: KNOWLEDGE GAPS FILLED

### Q1: Why Did greenlet Fail on Windows?

**What is greenlet?** A greenlet is a lightweight coroutine (micro-thread) implemented
in C. SQLAlchemy's async mode uses greenlets internally to bridge between the async
ORM layer and the underlying synchronous C-level database drivers.

When you install SQLAlchemy with `pip install sqlalchemy[asyncio]`, it installs `greenlet`.
The `greenlet` package contains a compiled C extension (`.pyd` file on Windows). This
C extension links against `MSVCP140.dll` — the Microsoft Visual C++ 2015-2022 Runtime.

**MSVCP140.dll:** Windows ships with many C++ runtimes. `MSVCP140.dll` is the one for
MSVC 2015+. Some minimal Windows installations (Docker images, VMs) don't include it.
Python distributions compiled with MSVC require it to load any C extension that links to it.

**The fix:** Install "Microsoft Visual C++ 2015-2022 Redistributable" from Microsoft's
download page. This installs `MSVCP140.dll` system-wide.

**Why Linux doesn't need this:** On Linux, C extensions link against `libc.so.6` and
`libstdc++.so.6`, which are part of every Linux distribution by default.

### Q2: Why Did Celery Use `localhost:6379` Instead of `redis:6379`?

This is the Docker networking bug described in Section 7.1.

The `.env` file contains:
```
REDIS_URL=redis://localhost:6379/0
```

This is correct when running backend directly on the host machine. Inside Docker Compose,
each container has its own network namespace. `localhost` inside the `celery_worker`
container is the celery_worker container itself — which has no Redis process.

The fix in `docker-compose.yml`:
```yaml
celery_worker:
    env_file: .env   ← loads REDIS_URL=redis://localhost:6379/0
    environment:
        - REDIS_URL=redis://redis:6379/0   ← OVERRIDES the env_file value
```

Docker Compose's `environment:` block takes precedence over `env_file:`. The service name
`redis` resolves to the Redis container's IP inside the Compose network via Docker's
embedded DNS.

### Q3: Why Did Swagger Show OAuth2 Form Instead of Bearer Input?

**OpenAPI security schemes:**

FastAPI's `OAuth2PasswordBearer` generates an OpenAPI security scheme that tells Swagger UI
to show a username/password form. This pops up a modal where you enter credentials — but
our login returns JSON tokens, not a form-compatible response.

```python
# The fix:
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)   # ← this one

# In custom_openapi() (main.py):
schemes["HTTPBearer"] = {"type": "http", "scheme": "bearer"}
```

`HTTPBearer` adds a simple "Value" text input to Swagger's Authorize dialog where you paste
the token directly. Both schemes are registered; whichever has a non-None value in the
request is used.

**The workflow:**
1. POST `/api/v1/auth/login` (in the Swagger form — this one accepts JSON body)
2. Copy `access_token` from response
3. Click "Authorize" → paste in the HTTPBearer "Value" field
4. All subsequent Swagger requests include `Authorization: Bearer <token>`

### Q4: Why Did Admin Revenue Show ₹0?

**The bug:** The seed script created orders with `status="paid"` but `paid_at=None`
(the column wasn't set when seeding).

The revenue query in `admin.py`:
```python
def _rev_q(start, end):
    date_col = func.coalesce(Order.paid_at, Order.created_at)
    # ↑ THE FIX: if paid_at is NULL, use created_at instead
    return select(func.coalesce(func.sum(Order.total), 0)).where(
        Order.status == "paid",
        date_col >= start,
        date_col < end,
    )
```

**Original broken query:**
```python
# Without coalesce:
.where(Order.status == "paid", Order.paid_at >= start_of_month)
# If paid_at is NULL: NULL >= start_of_month evaluates to NULL (not True)
# → all orders with NULL paid_at are filtered out → revenue = 0
```

**The fix** uses `COALESCE(paid_at, created_at)` — "use paid_at if it exists, otherwise
fall back to created_at." This makes seeded orders with `paid_at=NULL` still appear in
revenue calculations.

### Q5: Why Does the Frontend Show ₹NaN in Checkout?

**The bug:** Our backend returns `Decimal` values (PostgreSQL `NUMERIC`). Pydantic v2
serializes `Decimal` to JSON as **strings** (not numbers): `{"total": "1299.50"}`.

```typescript
// In CheckoutPage.tsx (before fix):
const tax = order.tax_amount * 0.18   // "1299.50" * 0.18 = NaN (string × number)
```

JavaScript string × number = NaN. NaN displayed as "₹NaN".

```typescript
// The fix: explicit Number() conversion
const tax = Number(order.tax_amount) * 0.18   // 1299.50 * 0.18 = 233.91 ✓
```

This is documented in our TypeScript types:
```typescript
export interface OrderItemResponse {
    unit_price: number;    // actually arrives as string from API — cast with Number()
    subtotal: number;
}
```

**Root cause:** Python's `decimal.Decimal` has no direct JSON equivalent. JSON only has
IEEE 754 floating point, which loses precision for financial values. Pydantic's choice
to serialize as string is correct (preserves precision) but requires frontend awareness.

### Q6: Why Does ngrok Need Authentication?

**What is ngrok?** A tunneling service that creates a public HTTPS URL
(`https://xxxx.ngrok.io`) that proxies traffic to your `localhost:8000`. Razorpay needs
a public URL to send webhooks — it can't POST to `localhost:8000`.

**Why newer agents need auth:** ngrok free tier changed its terms. The old agent could
create tunnels anonymously. The newer agent requires a free account and `ngrok authtoken`.

```bash
# One-time setup:
ngrok config add-authtoken <your-token>   # from ngrok.com/settings

# Then use:
ngrok http 8000
# Outputs: https://abc123.ngrok.io → http://localhost:8000
# Add this to Razorpay: https://abc123.ngrok.io/api/v1/orders/webhook
```

Every `ngrok http 8000` session generates a new `xxxx.ngrok.io` URL (free tier). This
means updating the Razorpay webhook URL every dev session. Paid ngrok gives a stable
subdomain.

### Q7: Why Did the `.wslconfig` Not Apply Immediately?

**What is WSL2?** Windows Subsystem for Linux 2 runs a real Linux kernel in a lightweight
Hyper-V VM. Docker Desktop uses WSL2 as its container runtime — all Docker containers
run inside the WSL2 VM, not Windows directly.

**The `.wslconfig` file** (`C:\Users\{User}\.wslconfig`) configures the WSL2 VM's
resources:
```ini
[wsl2]
memory=4GB
processors=4
swap=2GB
```

**Why restart is needed:** WSL2 is a running VM. `.wslconfig` is read when the VM starts.
Changing the file doesn't reconfigure a running VM — the change is pending until restart.

```bash
wsl --shutdown   # terminates the WSL2 VM immediately
# Next WSL2 / Docker Desktop start: reads the updated .wslconfig
```

On 8GB RAM machines: the WSL2 VM defaults to 50% of RAM = 4GB. With Elasticsearch
running inside Docker (inside WSL2), limiting WSL2 to 4GB + setting ES heap to 512MB
prevents the entire machine from being starved.

---

## SECTION 11: PRODUCTION DEPLOYMENT PLAN

### Production Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FREE TIER PRODUCTION STACK                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Vercel (Frontend)                                       │  │
│  │  Static React build → Global CDN → instant load         │  │
│  │  Auto-deploy on git push to main                        │  │
│  │  Env: VITE_API_URL, VITE_WS_URL                         │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │ HTTPS API calls                     │
│                           │ wss:// WebSocket                    │
│  ┌────────────────────────▼─────────────────────────────────┐  │
│  │  Render (Backend Web Service)                            │  │
│  │  FastAPI + Uvicorn                                       │  │
│  │  Auto-deploy on git push to main                        │  │
│  │  Health check: GET /health                              │  │
│  │  Free tier: sleeps after 15min inactivity               │  │
│  └──────┬─────────────┬──────────────┬─────────────────────┘  │
│         │             │              │                          │
│  ┌──────▼──┐  ┌───────▼─┐  ┌────────▼──────┐                 │
│  │Supabase │  │ Upstash  │  │  Bonsai.io    │                 │
│  │Postgres │  │  Redis   │  │ Elasticsearch │                 │
│  │Free:    │  │Free:     │  │Sandbox: 125MB │                 │
│  │500MB DB │  │10k cmd/d │  │Non-critical   │                 │
│  │No sleep │  │No sleep  │  │(fallback: DB) │                 │
│  └─────────┘  └──────────┘  └───────────────┘                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Render (Celery Worker — Background Worker service)      │  │
│  │  celery -A app.tasks.celery_app worker --concurrency 2  │  │
│  │  Reads from Upstash Redis                               │  │
│  │  Calls Resend API for email                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  AWS S3 (ap-south-1) — not free, but minimal cost       │  │
│  │  ~$0.025/GB/month for product images                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  UptimeRobot                                             │  │
│  │  Pings /health every 5 minutes                          │  │
│  │  Prevents Render free tier sleep                        │  │
│  │  Free: 50 monitors                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Environment Variable Differences: Local vs Production

| Variable | Local | Production |
|----------|-------|------------|
| `DATABASE_URL` | `postgresql+asyncpg://marketplace:marketplace@localhost:5432/marketplace` | Supabase direct connection URL (with `?ssl=require`) |
| `REDIS_URL` | `redis://localhost:6379/0` | `rediss://default:password@host.upstash.io:6379` (SSL!) |
| `ELASTICSEARCH_URL` | `http://localhost:9200` | `https://user:pass@host.bonsaisearch.net:443` |
| `RAZORPAY_KEY_ID` | `rzp_test_...` | `rzp_live_...` (switch after go-live) |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | `https://your-app.vercel.app` |
| `TEST_EMAIL_OVERRIDE` | Your email | Empty (real emails sent to real users) |
| `USE_LOCAL_STORAGE` | `false` (or `true` if no AWS) | `false` |
| `SENTRY_DSN` | Empty (optional) | Your Sentry DSN |

**Frontend production env vars** (in Vercel dashboard):
```
VITE_API_URL=https://your-backend.onrender.com
VITE_WS_URL=wss://your-backend.onrender.com   ← wss:// not ws:// for HTTPS backends
```

---

## SECTION 12: WHAT TO LEARN NEXT

### Already Implemented in This Codebase (understand these deeply)

| Topic | Where to find it | What to study |
|-------|-----------------|---------------|
| Async FastAPI + uvicorn | `app/main.py`, `app/api/v1/` | Lifespan, routers, middleware |
| JWT auth with refresh rotation | `app/core/security.py`, `app/core/deps.py` | Token creation, dependency chain |
| SQLAlchemy 2.x async ORM | `app/models/`, `app/crud/`, `app/core/database.py` | mapped_column, selectinload, sessions |
| Redis multi-use | `app/core/redis.py`, `app/services/cart.py` | Hash, TTL, SCAN, INCR patterns |
| Celery background tasks | `app/tasks/` | asyncio.run inside sync worker, retry |
| Razorpay webhook + HMAC | `app/services/razorpay.py`, `app/api/v1/orders.py` | Signature verification, idempotency |
| Pydantic v2 schemas | `app/schemas/` | Validators, Generic, from_attributes |
| React Query + Zustand | `frontend/src/hooks/`, `frontend/src/store/` | Server vs client state, invalidation |
| WebSocket real-time | `app/core/websocket.py`, `app/api/v1/ws.py` | ConnectionManager, WS auth pattern |
| Docker Compose orchestration | `docker-compose.yml` | Healthchecks, env overrides, networking |
| GitHub Actions CI/CD | `.github/workflows/ci.yml` | Service containers, matrix builds |

### Next to Learn — Ranked by Learning Value for This Project

#### 1. Database Query Optimization — `EXPLAIN ANALYZE`

**Add it here:** `app/crud/product.py → list_products()` and `app/crud/order.py → list_orders_by_seller()`

```sql
-- Run in psql after loading test data:
EXPLAIN ANALYZE SELECT * FROM products WHERE status = 'active' ORDER BY created_at DESC LIMIT 20;
-- Look for: Seq Scan (bad) vs Index Scan (good)
-- The second Alembic migration added indexes — verify they're used here
```

Learn: N+1 problem, EXPLAIN output (seq scan vs index scan vs bitmap heap scan), query
planner statistics, when `selectinload` helps and when it adds overhead.

**Why priority 1:** Our `list_orders_by_seller` uses a subquery — verify it's efficient
with a real data set before launch.

#### 2. Database Query Optimization — N+1 Problem

**Where this could bite us:** `admin.py → admin_list_orders()` uses `selectinload(Order.buyer)`
and `selectinload(Order.items).selectinload(OrderItem.product)`. For 100 orders, this
is 3 queries (not 300). But for complex admin reports, missing a `selectinload` would
silently cause N+1.

Learn: `sqlalchemy.event` to log all queries in development. `pytest-queries` library
to assert maximum query counts in tests.

#### 3. Nginx Reverse Proxy

**Add it here:** When moving from Render to a VPS (DigitalOcean, Linode).

```nginx
upstream fastapi {
    server 127.0.0.1:8000;
}
server {
    listen 443 ssl;
    location / { proxy_pass http://fastapi; }
    location /ws { proxy_pass http://fastapi; proxy_http_version 1.1;
                   proxy_set_header Upgrade $http_upgrade;
                   proxy_set_header Connection "upgrade"; }
}
```

Learn: WebSocket proxying (requires `Upgrade` header), SSL termination, rate limiting
at the proxy level (faster than application-level).

#### 4. Redis Pub/Sub for Multi-Worker WebSocket

**The current limitation:** Our `ConnectionManager` stores WebSocket connections in memory
(`defaultdict(list)`). If you run 2 FastAPI workers (`--workers 2`), a WebSocket
connection to worker 1 is invisible to worker 2. A webhook handled by worker 2 can't
notify a client connected to worker 1.

**Where to add it:** `app/core/websocket.py` — replace in-memory dict with Redis Pub/Sub.

```python
# When an event fires: publish to Redis channel
await redis.publish(f"user:{user_id}", json.dumps(message))

# Each worker subscribes and forwards to local WebSocket connections
async def redis_subscriber():
    async for message in pubsub.listen():
        # check if this worker has a WebSocket for this user
        if user_id in local_connections:
            await local_connections[user_id].send_json(data)
```

Learn: Redis Pub/Sub, async generators, process-local vs distributed state.

#### 5. Event Sourcing — Audit Log

**Where to add it:** New `app/models/order_event.py` table.

```python
class OrderEvent(Base):
    id: UUID
    order_id: UUID → FK orders.id
    event_type: str    # "created", "paid", "shipped", "cancelled"
    actor_id: UUID     # who triggered it
    payload: JSON      # snapshot of order at that moment
    created_at: datetime
```

Every status change writes an `OrderEvent`. The events are immutable. You can reconstruct
exactly what happened to any order and when.

Learn: event sourcing vs CRUD, CQRS pattern, audit trail requirements.

#### 6. Elasticsearch Aggregations for Faceted Search

**Add it here:** `app/services/search.py → search()` and `GET /api/v1/products`

```python
# Add to ES query:
"aggs": {
    "categories": {"terms": {"field": "category_name"}},  # count per category
    "price_ranges": {"range": {"field": "price", "ranges": [
        {"to": 500}, {"from": 500, "to": 2000}, {"from": 2000}
    ]}},
    "avg_rating": {"avg": {"field": "rating"}}
}
```

Frontend: show category counts and price range filters as checkboxes. Clicking a filter
re-runs the ES query with that filter applied.

Learn: bucket aggregations, nested aggregations, ES pagination (search_after for deep
pagination).

#### 7. Background Task Queue Monitoring — Flower

**Add it here:** New Docker Compose service.

```yaml
flower:
    image: mher/flower
    command: celery -A app.tasks.celery_app flower --port=5555
    ports: ["5555:5555"]
```

Flower provides a web UI showing: running tasks, queued tasks, task history, worker status,
retry counts. Essential for debugging email delivery failures.

Learn: Celery task states (PENDING, STARTED, SUCCESS, FAILURE, RETRY), task routing to
different queues, ETA-based scheduling.

#### 8. GraphQL with Strawberry

**Add it here:** New `app/api/graphql.py` — can coexist with REST endpoints.

```python
import strawberry
from strawberry.fastapi import GraphQLRouter

@strawberry.type
class ProductType:
    id: str
    title: str
    price: float

@strawberry.type
class Query:
    @strawberry.field
    async def product(self, slug: str, info: strawberry.types.Info) -> ProductType:
        db = info.context["db"]
        return await get_product_by_slug(db, slug)

schema = strawberry.Schema(query=Query)
app.include_router(GraphQLRouter(schema, context_getter=lambda: {"db": get_db()}))
```

Learn: GraphQL schema definition, resolver pattern, N+1 in GraphQL (DataLoader),
when REST is better (simple CRUD) vs GraphQL (complex nested data fetching).

---

*This document was generated from a fresh scan of all source files. Every code snippet
is verified against the actual codebase. Versions, routes, and behaviors reflect the
current state of the code.*
