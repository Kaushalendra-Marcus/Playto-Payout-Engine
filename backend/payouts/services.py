import logging
import uuid
from django.db import transaction, IntegrityError, OperationalError
from django.utils import timezone
from django.conf import settings
from .models import Merchant, Payout, LedgerEntry, BankAccount, IdempotencyKey

logger = logging.getLogger(__name__)


def get_or_create_idempotency_key(merchant, raw_key):
    // Attempt to create a new idempotency record atomically
    // If key already exists for this merchant, return the existing record
    // This is the first thing we do on any payout request - before any balance check
    expires_at = timezone.now() + timezone.timedelta(
        seconds=settings.IDEMPOTENCY_KEY_EXPIRY_SECONDS
    )
    try:
        record, created = IdempotencyKey.objects.get_or_create(
            merchant=merchant,
            key=raw_key,
            defaults={"expires_at": expires_at}
        )
        if not created and record.is_expired():
            // Expired keys can be reused - delete and recreate
            logger.info(
                "Idempotency key expired - reusing key=%s merchant_id=%s",
                raw_key, merchant.id
            )
            record.delete()
            record = IdempotencyKey.objects.create(
                merchant=merchant,
                key=raw_key,
                expires_at=expires_at
            )
            created = True
        return record, created
    except IntegrityError:
        // Race condition on creation - another request created the same key
        // This is normal under concurrent load - just fetch the existing one
        logger.warning(
            "Idempotency key race condition - fetching existing key=%s merchant_id=%s",
            raw_key, merchant.id
        )
        return IdempotencyKey.objects.get(merchant=merchant, key=raw_key), False


def create_payout(merchant_id, amount_paise, bank_account_id, idempotency_key_str):
    // Main entry point for creating a payout request
    // Returns (response_dict, http_status_code, is_duplicate)

    logger.info(
        "Payout request received - merchant_id=%s amount_paise=%s bank_account_id=%s key=%s",
        merchant_id, amount_paise, bank_account_id, idempotency_key_str
    )

    try:
        merchant = Merchant.objects.get(id=merchant_id)
    except Merchant.DoesNotExist:
        logger.error("Merchant not found - merchant_id=%s", merchant_id)
        return {"error": "Merchant not found"}, 404, False

    // Step 1: Get or create idempotency record
    // Done OUTSIDE the main transaction so the key is persisted immediately
    // This prevents a second in-flight request from creating a duplicate payout
    idem_record, is_new_key = get_or_create_idempotency_key(merchant, idempotency_key_str)

    if not is_new_key:
        // Key already exists - check if first request has completed
        if idem_record.is_complete and idem_record.response_body is not None:
            logger.info(
                "Returning cached idempotency response - key=%s merchant_id=%s",
                idempotency_key_str, merchant_id
            )
            return idem_record.response_body, idem_record.response_status_code, True
        else:
            // First request is still in flight - return 409 to tell client to retry
            logger.warning(
                "Idempotency key in flight - key=%s merchant_id=%s",
                idempotency_key_str, merchant_id
            )
            return {
                "error": "A request with this idempotency key is currently being processed. Retry shortly."
            }, 409, True

    // Step 2: Validate bank account belongs to this merchant
    try:
        bank_account = BankAccount.objects.get(id=bank_account_id, merchant=merchant)
    except BankAccount.DoesNotExist:
        logger.error(
            "Bank account not found or not owned by merchant - bank_account_id=%s merchant_id=%s",
            bank_account_id, merchant_id
        )
        // Clean up the idempotency record since we won't create a payout
        idem_record.delete()
        return {"error": "Bank account not found or does not belong to this merchant"}, 400, False

    // Step 3: Acquire row-level lock and check balance atomically
    // SELECT FOR UPDATE NOWAIT means:
    //   - Lock the merchant row so no other transaction can modify it
    //   - NOWAIT means fail immediately instead of waiting if locked (prevents deadlocks)
    //   - The balance check and payout creation happen in one atomic transaction
    //   - This is the only correct way to prevent the double-spend race condition

    try:
        with transaction.atomic():
            // Lock the merchant row - raises OperationalError immediately if locked by another transaction
            locked_merchant = Merchant.objects.select_for_update(nowait=True).get(id=merchant.id)

            available_balance = locked_merchant.get_available_balance()
            held_balance = locked_merchant.get_held_balance()
            spendable = available_balance - held_balance

            logger.debug(
                "Balance check - merchant_id=%s available=%s held=%s spendable=%s requested=%s",
                merchant_id, available_balance, held_balance, spendable, amount_paise
            )

            if amount_paise > spendable:
                // Insufficient funds - clean up idempotency key
                idem_record.delete()
                logger.warning(
                    "Insufficient balance - merchant_id=%s spendable=%s requested=%s",
                    merchant_id, spendable, amount_paise
                )
                return {
                    "error": "Insufficient balance",
                    "available_paise": spendable,
                    "requested_paise": amount_paise,
                }, 400, False

            // Create the payout record - funds are now "held"
            payout = Payout.objects.create(
                merchant=locked_merchant,
                bank_account=bank_account,
                amount_paise=amount_paise,
                status=Payout.PENDING,
            )

            // Link the idempotency key to this payout
            idem_record.payout = payout
            idem_record.save(update_fields=["payout"])

            logger.info(
                "Payout created - payout_id=%s merchant_id=%s amount_paise=%s",
                payout.id, merchant_id, amount_paise
            )

    except OperationalError as e:
        // Another transaction holds the lock on this merchant row
        // Return 409 so the client can retry
        logger.warning(
            "Could not acquire merchant lock - merchant_id=%s error=%s",
            merchant_id, str(e)
        )
        idem_record.delete()
        return {
            "error": "Another payout request is being processed. Please retry."
        }, 409, False

    // Step 4: Queue the payout for async processing
    from .tasks import process_payout
    process_payout.delay(str(payout.id))

    // Step 5: Build response and cache it in the idempotency record
    from .serializers import PayoutSerializer
    response_data = PayoutSerializer(payout).data
    // Convert UUID and datetime to JSON-serializable strings
    serializable_response = dict(response_data)

    idem_record.response_status_code = 201
    idem_record.response_body = serializable_response
    idem_record.is_complete = True
    idem_record.save(update_fields=["response_status_code", "response_body", "is_complete"])

    return serializable_response, 201, False
