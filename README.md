# Transaction Ledger API

A backend API for a simple transaction ledger. You can create accounts, post credit and debit transactions, read balances and history, and transfer money between accounts.

**Stack:** Python 3.14, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16, Docker.

## Run the app

You need Docker (Docker Desktop, OrbStack or Colima).

```bash
docker compose up --build
```

- The API starts on `http://localhost:8000`.
- Alembic migrations run before the server starts.
- Interactive API docs (Swagger UI) are at `http://localhost:8000/docs`.
- The OpenAPI schema is at `http://localhost:8000/openapi.json`.

If your Docker install has no `compose` plugin, use `docker-compose` with the same arguments.

## Run the tests

The tests use a real PostgreSQL database. They create a separate `ledger_test` database on the same server and migrate it with Alembic.

**In Docker:**

```bash
docker compose run --rm api pytest
```

**On your machine** (needs [uv](https://docs.astral.sh/uv/)):

```bash
docker compose up -d db
uv sync
uv run pytest
```

## Run without Docker for the API

```bash
docker compose up -d db
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Set `DATABASE_URL` to use a different PostgreSQL server. The default is `postgresql+psycopg://ledger:ledger@localhost:5432/ledger`.

## Project structure

The code follows a domain-led design. Each domain has its own package with the same layers.

```
app/
  accounts/        Account aggregate: open account, credit, debit, balance
  transactions/    Transaction entity: record, apply to account, history
  transfers/       Transfer: debit one account and credit another in one unit
  shared/          Config, database session, error types, error handlers, pagination
  main.py          FastAPI app and router registration
migrations/        Alembic migrations, one per domain table
tests/             Unit tests for domain rules and API tests per domain
```

In each domain package:

| File | Layer | Purpose |
|---|---|---|
| `domain.py` | Domain | Entities, business rules and domain errors. No FastAPI or SQLAlchemy. |
| `service.py` | Application | Use cases. Controls the database transaction. |
| `repository.py` | Infrastructure | Reads and writes domain objects with SQLAlchemy. |
| `models.py` | Infrastructure | Database tables and constraints. |
| `schemas.py` | API | Request and response models with validation. |
| `router.py` | API | HTTP endpoints. |

## How data integrity works

- **Atomic writes:** A transaction insert and the balance update run in one database transaction. If one step fails, the database rolls back both.
- **No race conditions:** The service locks the account row with `SELECT ... FOR UPDATE` before it changes the balance. Parallel debits on one account run one after the other, so the balance cannot go below zero.
- **Deadlock-free transfers:** A transfer locks both account rows in a fixed order (sorted by ID). Two opposite transfers cannot wait for each other.
- **Database constraints:**
  - `accounts.balance >= 0`
  - `accounts.name` is not blank
  - `transactions.amount > 0`
  - `transactions.type IN ('credit', 'debit')`
  - `UNIQUE (account_id, reference_id)` on transactions
  - Foreign key from `transactions.account_id` to `accounts.id`
- **Immutable transactions:** The API has no endpoint to edit or delete a transaction. The domain `Transaction` is a frozen dataclass.
- **Exact money:** Amounts and balances use `NUMERIC(18, 2)` in the database and `Decimal` in Python. Floats are never used.

## API documentation

Base path: `/api/v1`. All bodies are JSON.

### Endpoints

| Method | Path | Purpose | Success |
|---|---|---|---|
| `POST` | `/accounts` | Create an account | `201` |
| `GET` | `/accounts/{account_id}/balance` | Get the account balance | `200` |
| `POST` | `/accounts/{account_id}/transactions` | Add a credit or debit transaction | `201` |
| `GET` | `/accounts/{account_id}/transactions` | Get the transaction history | `200` |
| `POST` | `/transfers` | Transfer money between two accounts | `201` |
| `GET` | `/health` | Health check (no `/api/v1` prefix) | `200` |

### Create an account

```http
POST /api/v1/accounts
{"name": "Alice"}
```

```json
201 Created
{
  "id": "01a182d6-3ec7-7570-b401-2bab3197fb76",
  "name": "Alice",
  "balance": "0.00",
  "created_at": "2026-10-28T14:07:21.287326Z"
}
```

- `name` is required, 1 to 100 characters, trimmed.
- The server sets `id`, `balance` (always `0.00`) and `created_at`. A request that sends `balance`, `id` or `created_at` gets a `422`.

### Get the balance

```http
GET /api/v1/accounts/{account_id}/balance
```

```json
200 OK
{"account_id": "01a182d6-3ec7-7570-b401-2bab3197fb76", "balance": "150.00"}
```

### Add a transaction

```http
POST /api/v1/accounts/{account_id}/transactions
{"type": "credit", "amount": 50, "reference_id": "inv-1001", "description": "Invoice payment"}
```

```json
201 Created
{
  "id": "01a182d8-6413-765c-816e-79e435b65d10",
  "account_id": "01a182d6-3ec7-7570-b401-2bab3197fb76",
  "type": "credit",
  "amount": "50.00",
  "description": "Invoice payment",
  "reference_id": "inv-1001",
  "created_at": "2026-10-28T14:09:41.912345Z"
}
```

| Field | Rules |
|---|---|
| `type` | Required. `credit` or `debit`. |
| `amount` | Required. Greater than 0. At most 2 decimal places. Number or numeric string. |
| `reference_id` | Required. 1 to 100 characters, trimmed. Unique per account. |
| `description` | Optional. Up to 255 characters. |

### Get the transaction history

```http
GET /api/v1/accounts/{account_id}/transactions?type=debit&page=1&limit=20
```

| Query | Default | Rules |
|---|---|---|
| `type` | none (both types) | `credit` or `debit` |
| `page` | `1` | Integer, 1 or more |
| `limit` | `20` | Integer, 1 to 100 |

```json
200 OK
{
  "items": [{"id": "...", "type": "debit", "amount": "20.00", "...": "..."}],
  "page": 1,
  "limit": 20,
  "total": 2,
  "total_pages": 1
}
```

The items are sorted latest first by `created_at`.

### Transfer money

```http
POST /api/v1/transfers
{
  "source_account_id": "01a182d9-b75f-73bc-a6ec-7097fac389a8",
  "destination_account_id": "01a182d9-b781-7002-b198-2a1240942d66",
  "amount": 30,
  "reference_id": "transfer-1",
  "description": "Rent share"
}
```

```json
201 Created
{
  "debit":  {"account_id": "01a182d9-b75f-...", "type": "debit",  "amount": "30.00", "reference_id": "transfer-1", "...": "..."},
  "credit": {"account_id": "01a182d9-b781-...", "type": "credit", "amount": "30.00", "reference_id": "transfer-1", "...": "..."}
}
```

The transfer creates one debit on the source account and one credit on the destination account. Both use the same `reference_id`.

### Errors

All errors use one format:

```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "The account balance is too low for this debit.",
    "details": {"account_id": "...", "balance": "100.00", "amount": "150.00"}
  }
}
```

| Status | Code | When |
|---|---|---|
| `404` | `ACCOUNT_NOT_FOUND` | The account does not exist. |
| `404` | `HTTP_ERROR` | The route does not exist. |
| `405` | `HTTP_ERROR` | The method is not allowed, for example `DELETE` on transactions. |
| `409` | `DUPLICATE_TRANSACTION` | The account already has a transaction with this `reference_id`. `details.transaction_id` is the existing transaction. |
| `422` | `VALIDATION_ERROR` | The body, path or query is not valid. `details.fields` lists each field and the problem. This covers an invalid type, an invalid amount, invalid pagination, a malformed account ID and invalid JSON. |
| `422` | `INSUFFICIENT_BALANCE` | A debit or transfer is larger than the balance. |
| `422` | `SAME_ACCOUNT_TRANSFER` | The source and destination accounts are the same. |

## Assumptions

- **IDs** are UUIDv7. They are unique and sort by creation time, so the history order is stable when two rows have the same `created_at`.
- **Money** has 2 decimal places. The API returns amounts and balances as strings (for example `"150.00"`) so that no precision is lost in JSON. Requests accept numbers or numeric strings.
- **The maximum amount** is 16 digits before the decimal point (`NUMERIC(18, 2)`).
- **The account balance** is stored on the account row. It always equals the sum of credits minus the sum of debits, because both change in one database transaction.
- **A rejected transaction is not saved.** An insufficient-balance debit leaves no record. The client can retry with the same `reference_id`.
- **The duplicate check runs before the balance check.** A repeated `reference_id` always gets `409`, even if the debit would also fail for low balance.
- **Duplicate response:** The API returns `409 Conflict` with the ID of the existing transaction. It does not return the transaction again as a success.
- **`description`** is optional. The document lists it as a field but does not list it as a required validation.
- **Validation errors use `422`.** This is the FastAPI default for invalid input. Business rule failures (insufficient balance, same-account transfer) also use `422` because the request is valid in form but cannot be processed.
- **A page past the end** returns an empty `items` list with `200`, not an error.
- **Transfers** use one `reference_id` for both legs. Because `reference_id` is unique per account, a repeated transfer gets `409`. If the destination account already used that `reference_id`, the whole transfer rolls back.
- **A transfer to the same account** is rejected.
- **Authentication** is out of scope. The document does not ask for it.
