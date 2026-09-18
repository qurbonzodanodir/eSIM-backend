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

Monty settings are configured through environment variables; secrets are never
stored in source code:

```env
MONTY_CATALOG_BASE_URL=https://apis.montytelecom.com/catalog/api/reseller/v1
MONTY_CORE_BASE_URL=https://mm-hub-api.montytelecom.com/core/api/v1
MONTY_TENANT=
MONTY_API_KEY=
MONTY_BEARER_TOKEN=
MONTY_TIMEOUT_SECONDS=10
```

The current Monty client uses the documented bundle and order endpoints:
`/Bundle/get-all-basic/active`, `/Bundle/get-all-with-currency/active`,
`/order/create`, `/order/topup`, and
`/order/compatible-topup-with-currency`. Order history and consumption are
not implemented until Monty provides those endpoints in the current API
specification.

`GET /reseller/orders` returns the authenticated user's local order history
from PostgreSQL. It supports `order_id`, `order_reference`, `startDate`,
`endDate`, `page_number`, and `page_size`. `GET
/reseller/orders/consumption` remains unavailable until Monty documents a
consumption endpoint.

## Main endpoints

```text
POST /api/v1/auth/request-otp
POST /api/v1/auth/verify-otp
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/profile
POST /api/v1/profile/kyc/request
POST /api/v1/profile/kyc/mock-result (development only)
GET  /api/v1/catalog/operators
GET  /api/v1/catalog/operators/{operator_id}
GET  /api/v1/catalog/operators/{operator_id}/premium-numbers
GET  /api/v1/reseller/bundles
GET  /api/v1/countries
POST /api/v1/reseller/bundles/assign
GET  /api/v1/reseller/orders
GET  /api/v1/reseller/orders/consumption
GET  /api/v1/reseller/bundles/available-topup
GET  /health
```

The reseller bundle response exposes `price` as the customer-facing price.
Monty `cost` is an internal value and is not returned to the mobile app.
When assigning a bundle, the client must send `bundle_guid` from `recordGuid`;
`bundle_code` is a separate catalog identifier and must not be used as the GUID.
The bundle and country endpoints read exclusively from PostgreSQL. They make
no Monty calls. A separate worker downloads the full active catalog and publishes
it atomically. Bundles missing from a successful snapshot become inactive; an
incomplete, malformed, or empty default snapshot leaves the previous catalog intact.
Existing country presentation metadata (names, region, flags, operators and
popularity) is preserved. New countries receive `europe`, `middle_east`, `asia` or `other` from the ISO-code
mapping in `app/reseller/regions.py`, with an empty flag/operators list and zero
popularity. Successful syncs also fill existing `other` regions from this mapping,
including countries currently absent from Monty. Explicitly assigned regions are
preserved. Africa (except Egypt), the Americas and Oceania remain `other`. Turkey
is grouped in Asia, Russia and Cyprus in Europe, and Egypt in the Middle East. Countries without active bundles are
omitted from the public list. Multi-country bundles are linked to every supported
country; the public singular country fields retain Monty's first country for
compatibility.

### Catalog synchronization

After applying migrations, populate the catalog before routing mobile traffic:

```bash
uv run python -m app.reseller.worker --once
```

Run a separate supervised process alongside the API:

```bash
uv run python -m app.reseller.worker
```

It synchronizes immediately, then waits `MONTY_SYNC_INTERVAL_SECONDS` (default
3600) after each attempt. Configure the process supervisor to restart it on exit.
Alternatively, schedule `--once` hourly. PostgreSQL advisory locks prevent two
workers from synchronizing concurrently. No scheduler runs inside API workers.

The default Monty catalog is always downloaded. Set `MONTY_SYNC_CURRENCIES=USD,EUR`
to additionally download explicit currency variants through the same basic bundle
endpoint used previously. Every returned variant must match the requested currency;
a mismatch fails synchronization instead of publishing incorrectly labelled prices.
A currency filter can also use matching prices from the default catalog. Unavailable
currencies return an empty list; the service never converts prices itself.

`GET /reseller/bundles` keeps the existing response fields and query parameter names.
The default page size is now 20 and maximum is 100; clients should send explicit
pagination and follow `total`. Bundle name search is a case-insensitive literal
substring; bundle code and category are exact matches. Category tags are read from
`bundleCategoryTag` or `bundleCategory.tag` in the provider response. Confirm this
mapping against the tenant's actual payload before relying on category filtering.
Ordering is stable by bundle GUID. Before the first successful synchronization,
the catalog endpoints return empty lists.

Inspect synchronization status using:

```sql
SELECT last_attempt_at, last_success_at, error
FROM catalog_sync_state WHERE name = 'monty';
```

Monitor the age of `last_success_at` and worker failure logs. Catalog prices may be
up to a synchronization interval old (longer during outages); purchase-time price
and availability confirmation remains a separate concern of the order flow.

### Runtime limits and uncertain orders

Catalog downloads/publication have a total timeout of `MONTY_SYNC_TIMEOUT_SECONDS`
(default 300 seconds), in addition to the page limit and per-request Monty timeout.
Failed attempts retain the previous catalog. The worker waits the configured
interval after failures; it does not retry in a tight loop. Database statements
and lock waits are bounded by `DATABASE_STATEMENT_TIMEOUT_MS` (30000) and
`DATABASE_LOCK_TIMEOUT_MS` (5000).

Orders are committed locally as `PENDING` before calling Monty. A timeout, transport
failure, or ambiguous provider response leaves the order pending. Reusing its
reference returns 409 and never automatically purchases another eSIM. Reconcile
these orders with Monty before taking further action; automated reconciliation is
not implemented because the provider's order-status API is not available here.
The previous age-based `ORDER_PENDING_TIMEOUT_SECONDS` retry is no longer used.
Completed orders return their existing result; reusing a reference for a different
bundle returns 409. A new reference represents a new order and must not be generated
by mobile automatically after a timeout.

### Input validation and pagination

Invalid parameters return HTTP 422 in the existing validation error format.
Country/currency codes accept two/three ASCII letters and normalize to uppercase;
this checks format, not membership in an ISO registry. Text identifiers are trimmed,
nonempty and limited to 100 characters; names/search to 200 characters. Creating
an order requires a UUID `bundle_guid`, a valid email when supplied, and a valid
international phone number for `whatsapp_number` (the `whatsapp` alias is retained).
Refresh/logout tokens are nonempty, contain no whitespace and are at most 512
characters. OTP codes accept six ASCII digits.

All paginated endpoints accept `page_number` from 1 to 1,000,000 and `page_size`
from 1 to 100. Defaults: bundles 20, order history 50, premium numbers 20.
`GET /catalog/operators/{operator_id}/premium-numbers` still returns a JSON array;
request successive pages until a page contains fewer than `page_size` items.
Previously this endpoint returned every number, so mobile callers must now paginate
when displaying more than 20 numbers. Ties are resolved by ID for stable ordering.
Offset pagination can still shift when rows are inserted/deleted between requests.

Order history retains `startDate`/`endDate` query names. Both require an explicit
timezone (e.g. `2026-09-01T00:00:00Z`), with inclusive bounds and start <= end.
Requests previously using timestamps without a timezone must add one. The existing
response bodies remain unchanged. Apply migrations to install the new composite
indexes for order history and active premium-number pagination.

### Tests

The `tests/` directory is kept locally and excluded from Git. The commands below
require those local test files; a fresh clone does not include them.

```bash
uv run python -m unittest discover -s tests -v
# Optional PostgreSQL integration tests; each uses a temporary isolated schema:
TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost/esim_test \
  uv run python -m unittest discover -s tests -v
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
