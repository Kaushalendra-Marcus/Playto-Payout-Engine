# EXPLAINER.md

## 1. The Ledger

**Balance calculation query:**

```python
from django.db.models import Sum, Case, When, F, BigIntegerField

result = LedgerEntry.objects.filter(merchant=merchant).aggregate(
    total=Sum(
        Case(
            When(entry_type=LedgerEntry.CREDIT, then="amount_paise"),
            When(entry_type=LedgerEntry.DEBIT, then=F("amount_paise") * -1),
            output_field=BigIntegerField(),
        )
    )
)
balance = result["total"] or 0
```

**Why this model:**

The `LedgerEntry` table is the single source of truth for all money movement. Every credit (a customer payment arriving) and every debit (a payout completing) is a row. The merchant's balance is never stored as a column - it is always derived at query time from the aggregate.

This matters because:
- There is no "balance field" that can drift out of sync with the actual transaction history
- Records are immutable - a failed payout does not reverse a debit because no debit entry is created until a payout completes
- The invariant `sum(credits) - sum(debits) = displayed balance` is verifiable at any time via the `/invariant/` endpoint
- Amounts are always positive integers in paise. The `entry_type` field determines direction. This avoids signed integer confusion and makes aggregation SQL straightforward.

For held balance (funds reserved for pending payouts), I query `Payout` rows in `PENDING` status rather than creating a separate "hold" ledger entry. This keeps the ledger clean: a debit only appears when money actually leaves, not when it is merely reserved.

---

## 2. The Lock

**Exact code that prevents concurrent overdraw:**

```python
with transaction.atomic():
    locked_merchant = Merchant.objects.select_for_update(nowait=True).get(id=merchant.id)

    available_balance = locked_merchant.get_available_balance()
    held_balance = locked_merchant.get_held_balance()
    spendable = available_balance - held_balance

    if amount_paise > spendable:
        idem_record.delete()
        return {"error": "Insufficient balance"}, 400, False

    payout = Payout.objects.create(
        merchant=locked_merchant,
        bank_account=bank_account,
        amount_paise=amount_paise,
        status=Payout.PENDING,
    )
```

**Database primitive it relies on:**

`SELECT FOR UPDATE NOWAIT` in PostgreSQL. This is a row-level exclusive lock on the merchant row.

- `SELECT FOR UPDATE` tells PostgreSQL: "I am about to modify this row, lock it so no other transaction can read it with FOR UPDATE or modify it until I commit."
- `NOWAIT` means: "If the row is already locked by another transaction, raise an error immediately instead of waiting." This turns a potential deadlock or long wait into a clean, immediate rejection that the API layer can return as a 409.

The key insight is that the balance check and the payout creation happen inside the same `transaction.atomic()` block. Both operations see a consistent snapshot of the world. Without the lock, two concurrent requests could both pass the balance check before either one creates a payout - this is the classic check-then-act race condition. With the lock, only one transaction can hold the lock at a time, so the second request either waits or fails fast.

---

## 3. The Idempotency

**How the system knows it has seen a key before:**

The `IdempotencyKey` table has a `unique_together` constraint on `(merchant, key)`. When a request arrives:

1. We call `IdempotencyKey.objects.get_or_create(merchant=merchant, key=raw_key, ...)` outside the main payout transaction.
2. If `get_or_create` returns `created=False`, the key has been seen before.
3. If `is_complete=True` and `response_body` is populated, we return the cached response immediately without touching the payout logic.
4. If `is_complete=False`, the first request is still in flight - we return 409 so the client knows to retry shortly.

**What happens if the first request is in flight when the second arrives:**

The `IdempotencyKey` row is created at the very start of request processing, before any balance check or payout creation. The row starts with `is_complete=False`. When the second request calls `get_or_create`, it gets `created=False` and sees `is_complete=False`. It returns 409 immediately.

This is the correct behavior: telling the client "your request is being processed, retry in a moment" is better than either creating a duplicate or hanging indefinitely.

The `is_complete` flag is set to `True` only after the payout has been created and the response has been serialized and stored in `response_body`. This means the cache is only served once we have a complete response to cache.

Keys are scoped per merchant via `unique_together`. The same UUID key from two different merchants creates two independent records and two independent payouts.

Keys expire after 24 hours (`IDEMPOTENCY_KEY_EXPIRY_SECONDS = 86400`). Expired keys are deleted and recreated on next use, effectively resetting them.

---

## 4. The State Machine

**Where failed-to-completed (and all illegal transitions) are blocked:**

In `payouts/models.py`, the `Payout` model defines:

```python
VALID_TRANSITIONS = {
    PENDING: [PROCESSING],
    PROCESSING: [COMPLETED, FAILED],
    COMPLETED: [],
    FAILED: [],
}

def transition_to(self, new_status, failure_reason=None):
    if not self.can_transition_to(new_status):
        logger.error(
            "Illegal payout state transition attempted - payout_id=%s current=%s target=%s",
            self.id, self.status, new_status
        )
        raise ValueError(
            f"Cannot transition payout from {self.status} to {new_status}"
        )
    self.status = new_status
    if failure_reason:
        self.failure_reason = failure_reason
```

`COMPLETED: []` and `FAILED: []` are terminal states with no valid outgoing transitions. Any attempt to call `payout.transition_to(Payout.COMPLETED)` on a failed payout raises `ValueError` immediately before any field is mutated.

Every state change in the codebase goes through `transition_to()` - the tasks file never sets `payout.status` directly. This makes the state machine enforcement centralized and impossible to bypass accidentally.

---

## 5. The AI Audit

**What AI wrote, what I caught, what I replaced:**

AI's initial implementation of the balance check in `services.py`:

```python
# AI generated this
merchant = Merchant.objects.get(id=merchant_id)

credits = LedgerEntry.objects.filter(
    merchant=merchant, entry_type="credit"
).aggregate(total=Sum("amount_paise"))["total"] or 0

debits = LedgerEntry.objects.filter(
    merchant=merchant, entry_type="debit"
).aggregate(total=Sum("amount_paise"))["total"] or 0

balance = credits - debits

if amount_paise > balance:
    return {"error": "Insufficient balance"}, 400, False

payout = Payout.objects.create(...)
```

**Three problems I caught:**

1. No row-level lock. The `Merchant.objects.get()` is a plain read with no `select_for_update`. Two concurrent requests both pass the balance check, both create payouts, the balance goes negative. This is the exact overdraw bug the challenge warns about.

2. The balance check and payout creation are not inside `transaction.atomic()`. Even if the balance check passes, a context switch between the check and the create could let another request sneak in.

3. Held balance is not accounted for. The merchant might have 10000 paise available and a 7000 paise pending payout already. The AI's check would allow a second 6000 paise request even though only 3000 paise is truly spendable.

**What I replaced it with:**

```python
with transaction.atomic():
    locked_merchant = Merchant.objects.select_for_update(nowait=True).get(id=merchant.id)

    available_balance = locked_merchant.get_available_balance()
    held_balance = locked_merchant.get_held_balance()
    spendable = available_balance - held_balance

    if amount_paise > spendable:
        idem_record.delete()
        return {"error": "Insufficient balance", "available_paise": spendable}, 400, False

    payout = Payout.objects.create(...)
```

`select_for_update(nowait=True)` gives an exclusive row lock. The whole block is atomic. Spendable correctly deducts held funds. If two requests race, the second gets a `DatabaseError` (lock not available) which is caught and returned as 409.
