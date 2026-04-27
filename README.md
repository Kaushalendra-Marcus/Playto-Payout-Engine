# Playto Payout Engine

A minimal payout engine for Playto Pay. Merchants accumulate balance from international customer payments and withdraw to their Indian bank accounts. Built with Django, Celery, PostgreSQL, and React.

---

## Live Demo

Frontend: https://playto-payout-engine-v1.vercel.app/  
Backend: https://playto-payout-engine-production-08e6.up.railway.app

---

## Demo Screenshots
<img width="1919" height="1025" alt="image" src="https://github.com/user-attachments/assets/a18dc34a-e79c-4855-92ba-b0d07731257a" />
<img width="1919" height="1022" alt="image" src="https://github.com/user-attachments/assets/c7d8ff43-ee73-4295-ad1e-80f2738a8b91" />
<img width="1628" height="898" alt="image" src="https://github.com/user-attachments/assets/5822e807-b987-4055-a540-1954d39c8991" />

---

## Stack

- Backend: Django 4.2 + Django REST Framework
- Database: PostgreSQL (all amounts stored in paise as BigIntegerField)
- Background jobs: Celery + Redis
- Frontend: React 18 + Tailwind CSS + Vite

---

## Local Setup (Docker)

Requirements: Docker and Docker Compose

```bash
git clone <repo-url>
cd playto
docker compose up --build
````

Services started:

* PostgreSQL on port 5432
* Redis on port 6379
* Django backend on port 8000
* Celery worker
* Celery beat
* React frontend on port 5173

Open [http://localhost:5173](http://localhost:5173)

---

## Local Setup (Manual)

### Backend

```bash
cd backend

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

export DB_NAME=playto
export DB_USER=playto
export DB_PASSWORD=playto
export DB_HOST=localhost
export DB_PORT=5432
export REDIS_URL=redis://localhost:6379/0

createdb playto

python manage.py migrate
python seed.py

python manage.py runserver
```

---

### Celery Worker

```bash
cd backend
source venv/bin/activate
celery -A config worker --loglevel=info
```

---

### Celery Beat

```bash
cd backend
source venv/bin/activate
celery -A config beat --loglevel=info
```

---

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Running Tests

```bash
cd backend
python manage.py test payouts --verbosity=2
```

Tests included:

* Concurrency test ensures only one payout succeeds
* Overdraw rejection test
* Idempotency same key test
* Idempotency different key test
* Idempotency per merchant test
* State machine transition validation
* Ledger invariant validation

---

## API Reference

All endpoints under `/api/v1/`

```
GET  /merchants/
GET  /merchants/:id/
GET  /merchants/:id/ledger/
GET  /merchants/:id/payouts/
POST /merchants/:id/payouts/
GET  /merchants/:id/payouts/:id/
GET  /merchants/:id/invariant/
```

---

### Create Payout

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

Response:

```json
{
  "id": "...",
  "amount_paise": 50000,
  "amount_rupees": 500.0,
  "status": "pending",
  "bank_account": {},
  "attempt_count": 0,
  "failure_reason": null,
  "created_at": "...",
  "updated_at": "..."
}
```

Same idempotency key returns same response.

---

## Payout Lifecycle

```
POST payout request
-> idempotency key stored
-> merchant row locked using SELECT FOR UPDATE NOWAIT
-> balance check performed
-> payout created in pending state
-> task queued

Worker processes payout
-> pending -> processing
-> simulate bank response
-> 70 percent completed
-> 20 percent failed
-> 10 percent stuck

Scheduler retries stuck payouts
-> retries up to 3 times
-> then marks as failed
```

---

## Money Integrity Rules

* All amounts stored as integers in paise
* No float or decimal usage
* Balance computed using database aggregation
* Ledger entries are immutable
* Debit entry only created on completed payout
* Failed payout does not create debit entry
* Invariant: sum(credits) - sum(debits) = balance

---

## Environment Variables

| Variable             | Description       |
| -------------------- | ----------------- |
| SECRET_KEY           | Django secret     |
| DEBUG                | Debug mode        |
| DB_NAME              | Database name     |
| DB_USER              | Database user     |
| DB_PASSWORD          | Database password |
| DB_HOST              | Database host     |
| DB_PORT              | Database port     |
| REDIS_URL            | Redis connection  |
| ALLOWED_HOSTS        | Allowed hosts     |
| CORS_ALLOWED_ORIGINS | Frontend origins  |

---

## Notes

* Concurrency handled using database row-level locking
* Idempotency implemented per merchant using unique keys
* Background processing handled via Celery workers
* Retry logic ensures no payout remains stuck permanently

