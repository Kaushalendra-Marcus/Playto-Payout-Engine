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
    # Main payout processor -simulates bank settlement
    from .models import Payout

    logger.info("Processing payout - payout_id=%s", payout_id)

    # Lock row, check status, transition to PROCESSING - all in one atomic block
    try:
        with transaction.atomic():
            # select_related preloads merchant and bank_account in the same query
            # avoiding lazy loading issues inside later transactions
            payout = (
                Payout.objects
                .select_related("merchant", "bank_account")
                .select_for_update(nowait=True)
                .get(id=payout_id)
            )

            if payout.status != Payout.PENDING:
                logger.warning(
                    "Skipping payout - not in pending state - payout_id=%s status=%s",
                    payout_id, payout.status,
                )
                return

            payout.transition_to(Payout.PROCESSING)
            payout.attempt_count += 1
            payout.last_attempted_at = timezone.now()
            payout.save(update_fields=["status", "attempt_count", "last_attempted_at"])
            logger.info(
                "Payout moved to processing - payout_id=%s attempt=%s",
                payout_id, payout.attempt_count,
            )
    except Payout.DoesNotExist:
        logger.error("Payout not found - payout_id=%s", payout_id)
        return
    except Exception as e:
        logger.warning(
            "Could not acquire lock or transition payout - payout_id=%s error=%s",
            payout_id, str(e), exc_info=True,
        )
        return

    time.sleep(random.uniform(0.5, 2.0))

    outcome_roll = random.random()
    logger.info(
        "Payout outcome roll - payout_id=%s roll=%.3f",
        payout_id, outcome_roll,
    )

    if outcome_roll < 0.70:
        _complete_payout(payout)
    elif outcome_roll < 0.90:
        _fail_payout(payout, reason="Bank rejected the payout request")
    else:
        logger.warning(
            "Payout left hanging in processing - payout_id=%s (will be retried by beat)",
            payout_id,
        )


def _complete_payout(payout):
    from .models import LedgerEntry, Payout

    logger.info("Attempting to complete payout - payout_id=%s", payout.id)

    try:
        with transaction.atomic():
            fresh = (
                Payout.objects
                .select_related("merchant", "bank_account")
                .select_for_update()
                .get(id=payout.id)
            )

            if fresh.status != Payout.PROCESSING:
                logger.warning(
                    "Payout not in processing during completion - payout_id=%s status=%s",
                    fresh.id, fresh.status,
                )
                return

            fresh.transition_to(Payout.COMPLETED)
            fresh.save(update_fields=["status", "updated_at"])

            LedgerEntry.objects.create(
                merchant=fresh.merchant,
                amount_paise=fresh.amount_paise,
                entry_type=LedgerEntry.DEBIT,
                description=f"Payout to bank account {fresh.bank_account.account_number[-4:]}",
                payout=fresh,
            )
            logger.info(
                "Payout completed - payout_id=%s amount_paise=%s merchant=%s",
                fresh.id, fresh.amount_paise, fresh.merchant.name,
            )
    except Exception as e:
        logger.error(
            "Error completing payout - payout_id=%s error=%s",
            payout.id, str(e), exc_info=True,
        )


def _fail_payout(payout, reason="Payout failed"):
    # Atomically transition to failed
    from .models import Payout

    logger.info("Attempting to fail payout - payout_id=%s reason=%s", payout.id, reason)

    try:
        with transaction.atomic():
            fresh = (
                Payout.objects
                .select_related("merchant", "bank_account")
                .select_for_update()
                .get(id=payout.id)
            )

            if fresh.status not in [Payout.PROCESSING, Payout.PENDING]:
                logger.warning(
                    "Payout not in valid state for failure - payout_id=%s status=%s",
                    fresh.id, fresh.status,
                )
                return

            if fresh.status == Payout.PENDING:
                fresh.status = Payout.PROCESSING

            fresh.transition_to(Payout.FAILED, failure_reason=reason)
            fresh.save(update_fields=["status", "failure_reason", "updated_at"])
            logger.info(
                "Payout failed - payout_id=%s amount_paise=%s reason=%s",
                fresh.id, fresh.amount_paise, reason,
            )
    except Exception as e:
        logger.error(
            "Error failing payout - payout_id=%s error=%s",
            payout.id, str(e), exc_info=True,
        )


@shared_task
def retry_stuck_payouts():
    # Picks up payouts stuck in PROCESSING longer than threshold
    # Handles the 10% hang simulation and real-world timeouts
    from .models import Payout

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
            logger.warning(
                "Payout exceeded max retries - force failing - payout_id=%s attempts=%s",
                payout.id, payout.attempt_count,
            )
            try:
                with transaction.atomic():
                    fresh = Payout.objects.select_for_update().get(id=payout.id)
                    if fresh.status in [Payout.PROCESSING, Payout.PENDING]:
                        fresh.status = Payout.FAILED
                        fresh.failure_reason = f"Exceeded max retry attempts ({max_attempts})"
                        fresh.save(update_fields=["status", "failure_reason", "updated_at"])
                        logger.info("Payout force-failed - payout_id=%s", fresh.id)
            except Exception as e:
                logger.error(
                    "Error force-failing payout - payout_id=%s error=%s",
                    payout.id, str(e), exc_info=True,
                )
        else:
            logger.info(
                "Retrying stuck payout - payout_id=%s attempt=%s",
                payout.id, payout.attempt_count,
            )
            try:
                with transaction.atomic():
                    fresh = Payout.objects.select_for_update().get(id=payout.id)
                    if fresh.status == Payout.PROCESSING:
                        fresh.status = Payout.PENDING
                        fresh.save(update_fields=["status", "updated_at"])
                        process_payout.delay(str(fresh.id))
            except Exception as e:
                logger.error(
                    "Error retrying stuck payout - payout_id=%s error=%s",
                    payout.id, str(e), exc_info=True,
                )