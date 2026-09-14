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

Use `ENVIRONMENT=development` locally. In production, set a unique
`JWT_SECRET_KEY` with at least 32 characters and configure real SMS and
payment providers.

Development adapters are selected by default:

```env
SMS_PROVIDER=development
PAYMENT_PROVIDER=development
```

For SMS Center, set the provider and its send endpoint:

```env
SMS_PROVIDER=sms_center
SMS_API_URL=https://your-host/api/v1/sms/send
SMS_API_KEY=replace-with-secret
SMS_SENDER_NAME=TTelecom
SMS_TIMEOUT_SECONDS=10
SMS_OTP_TEMPLATE=Your verification code is {code}
```

The adapter sends `phone_number`, `message` and `source_addr` as JSON and
authenticates with the `X-API-Key` header.

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
POST /profile/kyc/request
POST /profile/kyc/mock-result (development only)
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

KYC currently uses an internal mock workflow. An authenticated user can submit
`POST /profile/kyc/request`, which changes the status to `PENDING`. In
development, `POST /profile/kyc/mock-result` can simulate a provider result
with `{"status":"VERIFIED"}` or `{"status":"NOT_VERIFIED"}`. The mock result
endpoint is disabled outside development. A real KYC provider can later
replace this adapter without changing the profile response contract.

## Database changes

Create a migration after changing models:

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

Do not commit `.env` or real provider credentials.
