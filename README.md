# Playto Payout Engine

A minimal payout engine for Playto Pay. Merchants accumulate balance from international customer payments and withdraw to their Indian bank accounts. Built with Django, Celery, PostgreSQL, and React.

---

## Stack

- Backend: Django 4.2 + Django REST Framework
- Database: PostgreSQL (all amounts in paise as BigIntegerField)
- Background jobs: Celery + Redis (real async, no sync faking)
- Frontend: React 18 + Tailwind CSS + Vite

---

## Local Setup (Docker - recommended)

**Requirements:** Docker and Docker Compose installed.

```bash
# Clone and start all services
git clone <repo-url>
cd playto
docker compose up --build
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- Django backend on port 8000 (runs migrations and seed automatically)
- Celery worker (processes payouts)
- Celery beat (retries stuck payouts every 30s)
- React frontend on port 5173

Open http://localhost:5173 to see the dashboard.

---

## Local Setup (Manual)

### Backend

```bash
cd backend

# Create and activate virtualenv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (or create .env)
export DB_NAME=playto
export DB_USER=playto
export DB_PASSWORD=playto
export DB_HOST=localhost
export DB_PORT=5432
export REDIS_URL=redis://localhost:6379/0

# Create the database
createdb playto

# Run migrations
python manage.py migrate

# Seed merchants and credit history
python seed.py

# Start Django
python manage.py runserver
```

### Celery worker (new terminal)

```bash
cd backend
source venv/bin/activate
celery -A config worker --loglevel=info
```

### Celery beat - retry stuck payouts (new terminal)

```bash
cd backend
source venv/bin/activate
celery -A config beat --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Running Tests

```bash
cd backend
python manage.py test payouts --verbosity=2
```

Tests included:
- `ConcurrencyTest.test_two_concurrent_payouts_only_one_succeeds` - fires two threads with overlapping payout requests, asserts exactly one 201
- `ConcurrencyTest.test_overdraw_rejected_cleanly` - single request over balance returns 400
- `IdempotencyTest.test_same_key_returns_same_response` - same key returns same payout ID, no duplicate in DB
- `IdempotencyTest.test_different_keys_create_different_payouts` - different keys create separate payouts
- `IdempotencyTest.test_key_scoped_per_merchant` - same key used by two merchants creates two payouts
- `StateMachineTest.test_illegal_transitions_rejected` - completed/failed payouts cannot transition
- `LedgerInvariantTest.test_balance_equals_credits_minus_debits` - invariant check passes

---

## API Reference

All endpoints are under `/api/v1/`.

```
GET  /merchants/
GET  /merchants/:id/
GET  /merchants/:id/ledger/
GET  /merchants/:id/payouts/
POST /merchants/:id/payouts/         Headers: Idempotency-Key: <uuid>
GET  /merchants/:id/payouts/:id/
GET  /merchants/:id/invariant/
```

### POST /merchants/:id/payouts/

Headers:
```
Content-Type: application/json
Idempotency-Key: <uuid>
```

Body:
```json
{
  "amount_paise": 50000,
  "bank_account_id": "<uuid>"
}
```

Response 201 (created):
```json
{
  "id": "...",
  "amount_paise": 50000,
  "amount_rupees": 500.0,
  "status": "pending",
  "bank_account": { ... },
  "attempt_count": 0,
  "failure_reason": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Second call with same `Idempotency-Key` returns the identical 201 response. No duplicate payout is created.

---

## Payout Lifecycle

```
POST /payouts
  -> idempotency key checked/created
  -> merchant row locked (SELECT FOR UPDATE NOWAIT)
  -> balance >= amount check
  -> Payout created (PENDING)
  -> Celery task queued

Celery worker picks up PENDING payout
  -> transitions to PROCESSING
  -> simulates bank call (0.5s - 2s delay)
  -> 70% - transitions to COMPLETED, creates DEBIT ledger entry
  -> 20% - transitions to FAILED, funds return (no debit entry needed)
  -> 10% - left in PROCESSING (simulates hang)

Celery beat runs every 30s
  -> finds payouts stuck in PROCESSING > 30s
  -> if attempt_count < 3: resets to PENDING, requeues
  -> if attempt_count >= 3: transitions to FAILED, funds return
```

---

## Money Integrity Rules

- All amounts stored as `BigIntegerField` in paise (1 INR = 100 paise)
- No `FloatField` or `DecimalField` anywhere in the codebase
- Balance is always `SUM(ledger entries)` - never a stored column
- Ledger entries are immutable - never updated or deleted
- A debit entry is only created when a payout reaches `COMPLETED`
- A failed payout returns funds by simply not creating a debit entry (the original credit remains)
- The `/invariant/` endpoint verifies `sum(credits) - sum(debits) = displayed balance` at any time

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | dev key | Django secret key |
| `DEBUG` | True | Django debug mode |
| `DB_NAME` | playto | PostgreSQL database name |
| `DB_USER` | playto | PostgreSQL user |
| `DB_PASSWORD` | playto | PostgreSQL password |
| `DB_HOST` | localhost | PostgreSQL host |
| `DB_PORT` | 5432 | PostgreSQL port |
| `REDIS_URL` | redis://localhost:6379/0 | Redis URL for Celery |
| `ALLOWED_HOSTS` | localhost,127.0.0.1 | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | http://localhost:5173 | Comma-separated CORS origins |
