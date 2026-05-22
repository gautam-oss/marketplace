# Marketplace

A full-stack multi-category e-commerce marketplace built with FastAPI, React, and PostgreSQL.

Buyers browse and purchase. Sellers list products. Admins moderate the platform.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.12, fully async) |
| ORM | SQLAlchemy 2.x async + Alembic |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Search | Elasticsearch 8.12 |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS |
| State | Zustand + React Query |
| Auth | JWT access + refresh tokens |
| Background | Celery + Redis broker |
| Payments | Razorpay (UPI / Cards / NetBanking) |
| Email | Resend SDK |
| Storage | AWS S3 (Mumbai region) |
| Monitoring | Sentry |

## Quick Start

### Prerequisites

- Docker Desktop with WSL2 backend
- Node.js 20+
- Python 3.12+

### 1. Clone and configure

```bash
git clone <repo-url>
cd marketplace
cp .env.example .env
# Edit .env with your real credentials
```

### 2. Start infrastructure services

```bash
docker compose up -d postgres redis elasticsearch
```

### 3. Run backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# or: .venv\Scripts\Activate.ps1   (PowerShell)

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `ELASTICSEARCH_URL` | Elasticsearch URL |
| `SECRET_KEY` | JWT signing secret (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `RAZORPAY_KEY_ID` | Razorpay test/live key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay secret |
| `RESEND_API_KEY` | Resend API key for emails |
| `EMAIL_FROM` | Sender email address |
| `AWS_ACCESS_KEY_ID` | AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret |
| `S3_BUCKET_NAME` | S3 bucket name |
| `SENTRY_DSN` | Sentry DSN (optional) |

## API

Base URL: `http://localhost:8000/api/v1`

Interactive docs: http://localhost:8000/docs

| Route | Description |
|---|---|
| `POST /auth/register` | Register new buyer account |
| `POST /auth/login` | Login, returns JWT tokens |
| `GET /products` | List active products (filterable) |
| `GET /products/{slug}` | Product detail |
| `POST /orders/checkout` | Create order + Razorpay order |
| `POST /orders/webhook` | Razorpay payment webhook |
| `GET /admin/stats` | Platform statistics (admin only) |

## Testing

```bash
# Start test DB
docker compose up -d postgres redis

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing
```

105 tests across auth, products, orders, cart, reviews, categories, admin.

## Payments (Razorpay)

1. Buyer checks out → backend creates Razorpay order
2. Frontend opens Razorpay checkout modal
3. Razorpay POSTs to `/api/v1/orders/webhook` on payment captured
4. Backend verifies signature → marks order paid → sends confirmation email

For local webhook testing, use ngrok:
```bash
ngrok http 8000
# Add https://xxxx.ngrok.io/api/v1/orders/webhook to Razorpay dashboard
```

## Production Deployment

```bash
# Backend
docker build -f backend/Dockerfile.prod -t marketplace-backend ./backend

# Frontend
docker build -f frontend/Dockerfile.prod -t marketplace-frontend ./frontend
```

## CI/CD

GitHub Actions runs on every push to `main` or `develop`:
- **backend-test**: PostgreSQL + Redis service containers, runs pytest
- **backend-lint**: ruff linting
- **frontend-build**: TypeScript type check + Vite build

## Project Structure

```
marketplace/
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/v1/   # Route handlers
│   │   ├── core/     # Config, DB, auth, deps
│   │   ├── crud/     # Database queries
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic v2 schemas
│   │   ├── services/ # Elasticsearch, S3, Razorpay, cart
│   │   └── tasks/    # Celery background tasks
│   └── alembic/      # Database migrations
├── frontend/         # React application
│   └── src/
│       ├── api/      # Axios API client
│       ├── components/
│       ├── hooks/    # React Query hooks
│       ├── pages/    # Route pages
│       ├── store/    # Zustand stores
│       └── types/    # TypeScript interfaces
└── tests/            # pytest test suite
```
