import uuid
import logging
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})"

    def get_available_balance(self):
        // Available balance = total credits - total debits via database aggregation
        // Never compute this in Python on fetched rows
        from django.db.models import Sum, Q
        result = LedgerEntry.objects.filter(merchant=self).aggregate(
            total=Sum(
                models.Case(
                    models.When(entry_type=LedgerEntry.CREDIT, then="amount_paise"),
                    models.When(entry_type=LedgerEntry.DEBIT, then=models.F("amount_paise") * -1),
                    output_field=models.BigIntegerField(),
                )
            )
        )
        return result["total"] or 0

    def get_held_balance(self):
        // Held balance = sum of all pending payouts (funds reserved but not yet processed)
        from django.db.models import Sum
        result = Payout.objects.filter(
            merchant=self,
            status=Payout.PENDING
        ).aggregate(total=Sum("amount_paise"))
        return result["total"] or 0

    class Meta:
        ordering = ["name"]


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="bank_accounts")
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account_holder_name} - {self.account_number[-4:].zfill(4)}"

    class Meta:
        ordering = ["-is_primary", "created_at"]


class LedgerEntry(models.Model):
    CREDIT = "credit"
    DEBIT = "debit"
    ENTRY_TYPE_CHOICES = [
        (CREDIT, "Credit"),
        (DEBIT, "Debit"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="ledger_entries")

    // Amount always stored as positive integer in paise (1 INR = 100 paise)
    // The entry_type field determines whether it adds or subtracts from balance
    amount_paise = models.BigIntegerField()

    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES)

    // Human-readable description for dashboard display
    description = models.CharField(max_length=500)

    // Reference to the payout that caused this entry, if applicable
    payout = models.ForeignKey(
        "Payout",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ledger_entries"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    // Ledger entries are immutable - never update or delete them
    // To reverse a transaction, create a new entry with opposite type

    def __str__(self):
        direction = "+" if self.entry_type == self.CREDIT else "-"
        return f"{direction}{self.amount_paise} paise for {self.merchant.name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "-created_at"]),
            models.Index(fields=["merchant", "entry_type"]),
        ]


class Payout(models.Model):
    // State machine: PENDING -> PROCESSING -> COMPLETED or FAILED
    // Any other transition is illegal and will be rejected
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (COMPLETED, "Completed"),
        (FAILED, "Failed"),
    ]

    // Legal forward transitions only
    VALID_TRANSITIONS = {
        PENDING: [PROCESSING],
        PROCESSING: [COMPLETED, FAILED],
        COMPLETED: [],
        FAILED: [],
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="payouts")
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="payouts")

    // Always paise, always BigIntegerField, never float or decimal
    amount_paise = models.BigIntegerField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    // Retry tracking
    attempt_count = models.IntegerField(default=0)
    last_attempted_at = models.DateTimeField(null=True, blank=True)

    // Failure reason for debugging and display
    failure_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_transition_to(self, new_status):
        // Check if transition is allowed by the state machine
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def transition_to(self, new_status, failure_reason=None):
        // Enforce state machine - reject illegal transitions
        if not self.can_transition_to(new_status):
            logger.error(
                "Illegal payout state transition attempted - payout_id=%s current=%s target=%s",
                self.id, self.status, new_status
            )
            raise ValueError(
                f"Cannot transition payout from {self.status} to {new_status}"
            )
        logger.info(
            "Payout state transition - payout_id=%s %s -> %s",
            self.id, self.status, new_status
        )
        self.status = new_status
        if failure_reason:
            self.failure_reason = failure_reason

    def __str__(self):
        return f"Payout {self.id} - {self.amount_paise} paise - {self.status}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["merchant", "-created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["status", "last_attempted_at"]),
        ]


class IdempotencyKey(models.Model):
    // Idempotency keys are scoped per merchant
    // Same key from two different merchants are treated as different requests
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="idempotency_keys")
    key = models.CharField(max_length=255)

    // Cached response - stored on first completion so second call returns identical response
    response_status_code = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)

    // Track the payout this key created
    payout = models.OneToOneField(
        Payout,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="idempotency_key"
    )

    // Whether the first request has finished processing (used for in-flight detection)
    is_complete = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"IdempotencyKey {self.key} for {self.merchant.name}"

    class Meta:
        // Composite unique constraint - key scoped to merchant
        unique_together = [("merchant", "key")]
        indexes = [
            models.Index(fields=["merchant", "key"]),
            models.Index(fields=["expires_at"]),
        ]
