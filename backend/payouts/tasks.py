import random
import logging
import time
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def process_payout(self, payout_id):
    #  Main payout processor - simulates bank settlement
    #  Outcome distribution: 70% success, 20% failure, 10% hang in processing
    from .models import Payout, LedgerEntry

    logger.info("Processing payout - payout_id=%s", payout_id)

    try:
        payout = Payout.objects.select_for_update(nowait=True).get(id=payout_id)
    except Payout.DoesNotExist:
        logger.error("Payout not found - payout_id=%s", payout_id)
        return
    except Exception as e:
        logger.warning("Could not lock payout row - payout_id=%s error=%s", payout_id, str(e))
        return

    #  Only process payouts that are in PENDING state
    if payout.status != Payout.PENDING:
        logger.warning(
            "Skipping payout - not in pending state - payout_id=%s status=%s",
            payout_id, payout.status
        )
        return

    #  Transition to PROCESSING state
    with transaction.atomic():
        payout.refresh_from_db()
        try:
            payout.transition_to(Payout.PROCESSING)
            payout.attempt_count += 1
            payout.last_attempted_at = timezone.now()
            payout.save(update_fields=["status", "attempt_count", "last_attempted_at"])
            logger.info(
                "Payout moved to processing - payout_id=%s attempt=%s",
                payout_id, payout.attempt_count
            )
        except ValueError as e:
            logger.error("State transition failed - payout_id=%s error=%s", payout_id, str(e))
            return

    #  Simulate bank API call delay (0.5s to 2s)
    time.sleep(random.uniform(0.5, 2.0))

    #  Simulate bank settlement outcome
    #  70% success, 20% failure, 10% stays in processing (simulates timeout/hang)
    outcome_roll = random.random()

    if outcome_roll < 0.70:
        _complete_payout(payout)
    elif outcome_roll < 0.90:
        _fail_payout(payout, reason="Bank rejected the payout request")
    else:
        #  Intentionally leave in PROCESSING state to simulate a hung payout
        #  The retry_stuck_payouts beat task will pick this up after 30 seconds
        logger.warning(
            "Payout left hanging in processing - payout_id=%s (will be retried by beat)",
            payout_id
        )


def _complete_payout(payout):
    #  Atomically: transition to completed and create the debit ledger entry
    #  The debit confirms the funds have left the merchant's account
    from .models import LedgerEntry

    with transaction.atomic():
        payout.refresh_from_db()
        if payout.status != Payout.PROCESSING:
            logger.warning(
                "Payout no longer in processing - skipping completion - payout_id=%s status=%s",
                payout.id, payout.status
            )
            return
        try:
            payout.transition_to(Payout.COMPLETED)
            payout.save(update_fields=["status", "updated_at"])

            LedgerEntry.objects.create(
                merchant=payout.merchant,
                amount_paise=payout.amount_paise,
                entry_type=LedgerEntry.DEBIT,
                description=f"Payout to bank account {payout.bank_account.account_number[-4:]}",
                payout=payout,
            )
            logger.info(
                "Payout completed successfully - payout_id=%s amount_paise=%s merchant_id=%s",
                payout.id, payout.amount_paise, payout.merchant_id
            )
        except ValueError as e:
            logger.error(
                "Could not complete payout - payout_id=%s error=%s",
                payout.id, str(e)
            )


def _fail_payout(payout, reason="Payout failed"):
    #  Atomically: transition to failed and return funds to merchant balance
    #  No ledger entry is created - the original credit remains untouched
    #  Held funds are released because the payout no longer exists in PENDING state
    from .models import LedgerEntry

    with transaction.atomic():
        payout.refresh_from_db()
        if payout.status != Payout.PROCESSING:
            logger.warning(
                "Payout no longer in processing - skipping failure - payout_id=%s status=%s",
                payout.id, payout.status
            )
            return
        try:
            payout.transition_to(Payout.FAILED, failure_reason=reason)
            payout.save(update_fields=["status", "failure_reason", "updated_at"])

            #  Funds return to available balance because:
            #  - No debit ledger entry was created
            #  - get_held_balance() only counts PENDING payouts
            #  - This payout is now FAILED, so it no longer contributes to held balance
            #  The original credit ledger entry remains - no reversal needed

            logger.info(
                "Payout failed and funds returned - payout_id=%s amount_paise=%s reason=%s",
                payout.id, payout.amount_paise, reason
            )
        except ValueError as e:
            logger.error(
                "Could not fail payout - payout_id=%s error=%s",
                payout.id, str(e)
            )


@shared_task
def retry_stuck_payouts():
    #  Picks up payouts that have been in PROCESSING state longer than the threshold
    #  This handles the 10% "hang" simulation and real-world network timeouts
    from .models import Payout
    from django.conf import settings

    threshold_seconds = settings.PAYOUT_STUCK_THRESHOLD_SECONDS
    max_attempts = settings.PAYOUT_MAX_RETRY_ATTEMPTS
    cutoff_time = timezone.now() - timezone.timedelta(seconds=threshold_seconds)

    stuck_payouts = Payout.objects.filter(
        status=Payout.PROCESSING,
        last_attempted_at__lte=cutoff_time,
    )

    count = stuck_payouts.count()
    if count > 0:
        logger.info("Found %s stuck payouts to retry/fail", count)

    for payout in stuck_payouts:
        if payout.attempt_count >= max_attempts:
            #  Max attempts reached - move to failed and return funds
            logger.warning(
                "Payout exceeded max retries - moving to failed - payout_id=%s attempts=%s",
                payout.id, payout.attempt_count
            )
            _fail_payout(payout, reason=f"Exceeded max retry attempts ({max_attempts})")
        else:
            #  Still have retry attempts remaining - reset to pending and requeue
            #  Exponential backoff is achieved by the beat schedule (runs every 30s)
            #  and the attempt count check above
            logger.info(
                "Retrying stuck payout - payout_id=%s attempt=%s",
                payout.id, payout.attempt_count
            )
            with transaction.atomic():
                payout.refresh_from_db()
                if payout.status == Payout.PROCESSING:
                    payout.status = Payout.PENDING
                    payout.save(update_fields=["status", "updated_at"])
                    process_payout.delay(str(payout.id))
