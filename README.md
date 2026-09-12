# eSIM Reseller Service

FastAPI backend with PostgreSQL, async SQLAlchemy, Alembic, OTP authentication, local eSIM catalog, and Monty reseller integration.

## Requirements

- Python 3.12+
- uv
- PostgreSQL 17+

## Local setup

```bash
uv sync
cp .env.example .env
createdb esim_db
uv run alembic upgrade head
uv run python -m app.catalog.seed
uv run uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

## Configuration

`DATABASE_URL` must use the async PostgreSQL driver:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/esim_db
```

Monty settings are optional until upstream credentials are available:

```env
MONTY_BASE_URL=
MONTY_USERNAME=
MONTY_PASSWORD=
MONTY_TIMEOUT_SECONDS=10
```

## Main endpoints

```text
POST /auth/request-otp
POST /auth/verify-otp
POST /auth/refresh
POST /auth/logout
GET  /profile
GET  /catalog/operators
GET  /catalog/operators/{operator_id}
GET  /catalog/operators/{operator_id}/premium-numbers
GET  /reseller/bundles
POST /reseller/bundles/assign
GET  /reseller/orders
GET  /reseller/orders/consumption
GET  /reseller/bundles/available-topup
GET  /health
```

The development SMS and payment adapters are placeholders. Real provider adapters can be added without changing the auth or profile services.

## Database changes

Create a migration after changing models:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Do not commit `.env` or real provider credentials.
