import uuid
import threading
import logging
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from payouts.models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey
from payouts.services import create_payout

logger = logging.getLogger(__name__)


def _create_test_merchant(name="Test Merchant", email=None):
    #  Helper to create a merchant with a bank account and initial credit
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    merchant = Merchant.objects.create(name=name, email=email)
    bank_account = BankAccount.objects.create(
        merchant=merchant,
        account_number="1234567890123456",
        ifsc_code="TEST0001234",
        account_holder_name=name,
        is_primary=True,
    )
    return merchant, bank_account


class ConcurrencyTest(TransactionTestCase):
    #  TransactionTestCase is required for testing concurrency
    #  because TestCase wraps everything in a single transaction
    #  which would make select_for_update behave differently

    def test_two_concurrent_payouts_only_one_succeeds(self):
        #  A merchant with 100 rupees (10000 paise) submits two simultaneous
        #  60 rupee (6000 paise) payout requests.
        #  Exactly one must succeed and one must be rejected.

        merchant, bank_account = _create_test_merchant(name="Concurrency Test Merchant")

        #  Fund the merchant with 10000 paise (100 rupees)
        LedgerEntry.objects.create(
            merchant=merchant,
            amount_paise=10000,
            entry_type=LedgerEntry.CREDIT,
            description="Test funding",
        )

        initial_balance = merchant.get_available_balance()
        self.assertEqual(initial_balance, 10000, "Merchant should start with 10000 paise")

        results = []
        errors = []

        def attempt_payout(key_suffix):
            #  Each thread uses a unique idempotency key
            try:
                response_data, http_status, is_duplicate = create_payout(
                    merchant_id=merchant.id,
                    amount_paise=6000,
                    bank_account_id=bank_account.id,
                    idempotency_key_str=f"concurrent-test-key-{key_suffix}",
                )
                results.append(http_status)
                logger.info("Thread %s got status %s", key_suffix, http_status)
            except Exception as e:
                errors.append(str(e))
                logger.error("Thread %s got error: %s", key_suffix, str(e))

        #  Fire two threads simultaneously
        t1 = threading.Thread(target=attempt_payout, args=("A",))
        t2 = threading.Thread(target=attempt_payout, args=("B",))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f"No exceptions should occur. Got: {errors}")
        self.assertEqual(len(results), 2, "Both threads should return a result")

        success_count = results.count(201)
        rejection_count = sum(1 for s in results if s in [400, 409])

        logger.info(
            "Concurrency test results - 201s=%s rejections=%s",
            success_count, rejection_count
        )

        #  Exactly one request must succeed and one must be rejected
        self.assertEqual(success_count, 1, "Exactly one payout should be created")
        self.assertEqual(rejection_count, 1, "Exactly one payout should be rejected")

        #  Verify the balance invariant still holds after concurrent requests
        merchant.refresh_from_db()
        pending_payouts = Payout.objects.filter(merchant=merchant, status=Payout.PENDING)
        self.assertEqual(pending_payouts.count(), 1, "Only one pending payout should exist")

        held = merchant.get_held_balance()
        spendable = merchant.get_available_balance() - held
        #  Spendable should be 10000 - 6000 = 4000 paise
        self.assertEqual(spendable, 4000, "Spendable balance should be 4000 paise after one 6000 hold")

        logger.info("Concurrency test passed - balance integrity maintained")

    def test_overdraw_rejected_cleanly(self):
        #  Single request for more than available balance must be rejected
        merchant, bank_account = _create_test_merchant(name="Overdraw Test Merchant")
        LedgerEntry.objects.create(
            merchant=merchant,
            amount_paise=5000,
            entry_type=LedgerEntry.CREDIT,
            description="Test funding",
        )

        response_data, http_status, _ = create_payout(
            merchant_id=merchant.id,
            amount_paise=9999,
            bank_account_id=bank_account.id,
            idempotency_key_str=str(uuid.uuid4()),
        )

        self.assertEqual(http_status, 400)
        self.assertIn("Insufficient balance", response_data.get("error", ""))
        self.assertEqual(Payout.objects.filter(merchant=merchant).count(), 0)
        logger.info("Overdraw test passed - rejected cleanly")


class IdempotencyTest(TransactionTestCase):

    def test_same_key_returns_same_response(self):
        #  Calling POST /payouts twice with the same idempotency key
        #  must return the exact same response - no duplicate payout created

        merchant, bank_account = _create_test_merchant(name="Idempotency Test Merchant")
        LedgerEntry.objects.create(
            merchant=merchant,
            amount_paise=20000,
            entry_type=LedgerEntry.CREDIT,
            description="Test funding",
        )

        key = str(uuid.uuid4())

        #  First call
        response1, status1, is_dup1 = create_payout(
            merchant_id=merchant.id,
            amount_paise=5000,
            bank_account_id=bank_account.id,
            idempotency_key_str=key,
        )

        #  Second call - same key
        response2, status2, is_dup2 = create_payout(
            merchant_id=merchant.id,
            amount_paise=5000,
            bank_account_id=bank_account.id,
            idempotency_key_str=key,
        )

        logger.info("Idempotency test - status1=%s status2=%s is_dup2=%s", status1, status2, is_dup2)

        self.assertEqual(status1, 201, "First call should create payout")
        self.assertEqual(status2, 201, "Second call should return same 201")
        self.assertTrue(is_dup2, "Second call should be marked as duplicate")

        #  Responses must be identical
        self.assertEqual(response1["id"], response2["id"], "Payout IDs must be identical")

        #  Only one payout should exist in the database
        payout_count = Payout.objects.filter(merchant=merchant).count()
        self.assertEqual(payout_count, 1, "Only one payout should exist in DB")

        logger.info("Idempotency test passed - no duplicate created")

    def test_different_keys_create_different_payouts(self):
        #  Two calls with different keys must create two separate payouts

        merchant, bank_account = _create_test_merchant(name="Different Keys Test Merchant")
        LedgerEntry.objects.create(
            merchant=merchant,
            amount_paise=20000,
            entry_type=LedgerEntry.CREDIT,
            description="Test funding",
        )

        _, status1, _ = create_payout(
            merchant_id=merchant.id,
            amount_paise=5000,
            bank_account_id=bank_account.id,
            idempotency_key_str=str(uuid.uuid4()),
        )
        _, status2, _ = create_payout(
            merchant_id=merchant.id,
            amount_paise=5000,
            bank_account_id=bank_account.id,
            idempotency_key_str=str(uuid.uuid4()),
        )

        self.assertEqual(status1, 201)
        self.assertEqual(status2, 201)
        self.assertEqual(Payout.objects.filter(merchant=merchant).count(), 2)

    def test_key_scoped_per_merchant(self):
        #  Same idempotency key used by two different merchants must
        #  create two separate payouts - keys are scoped per merchant

        m1, ba1 = _create_test_merchant(name="Merchant One")
        m2, ba2 = _create_test_merchant(name="Merchant Two")

        for m in [m1, m2]:
            LedgerEntry.objects.create(
                merchant=m,
                amount_paise=20000,
                entry_type=LedgerEntry.CREDIT,
                description="Test funding",
            )

        shared_key = "shared-key-across-merchants"

        _, status1, _ = create_payout(
            merchant_id=m1.id,
            amount_paise=5000,
            bank_account_id=ba1.id,
            idempotency_key_str=shared_key,
        )
        _, status2, _ = create_payout(
            merchant_id=m2.id,
            amount_paise=5000,
            bank_account_id=ba2.id,
            idempotency_key_str=shared_key,
        )

        self.assertEqual(status1, 201)
        self.assertEqual(status2, 201)
        self.assertEqual(Payout.objects.count(), 2, "Each merchant should have their own payout")
        logger.info("Key scoping test passed")


class StateMachineTest(TestCase):

    def test_illegal_transitions_rejected(self):
        #  Verify that the state machine rejects invalid transitions
        merchant, bank_account = _create_test_merchant()

        payout = Payout.objects.create(
            merchant=merchant,
            bank_account=bank_account,
            amount_paise=1000,
            status=Payout.COMPLETED,
        )

        #  completed -> pending is illegal
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.PENDING)

        #  completed -> processing is illegal
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.PROCESSING)

        #  completed -> failed is illegal
        with self.assertRaises(ValueError):
            payout.transition_to(Payout.FAILED)

        logger.info("State machine illegal transition test passed")

    def test_legal_transitions_allowed(self):
        merchant, bank_account = _create_test_merchant()

        payout = Payout.objects.create(
            merchant=merchant,
            bank_account=bank_account,
            amount_paise=1000,
            status=Payout.PENDING,
        )

        #  pending -> processing is legal
        payout.transition_to(Payout.PROCESSING)
        self.assertEqual(payout.status, Payout.PROCESSING)

        #  processing -> completed is legal
        payout.transition_to(Payout.COMPLETED)
        self.assertEqual(payout.status, Payout.COMPLETED)

        logger.info("State machine legal transition test passed")


class LedgerInvariantTest(TestCase):

    def test_balance_equals_credits_minus_debits(self):
        #  The displayed balance must always equal sum(credits) - sum(debits)
        #  This is the core money integrity invariant

        merchant, _ = _create_test_merchant()

        LedgerEntry.objects.create(merchant=merchant, amount_paise=10000, entry_type="credit", description="Credit 1")
        LedgerEntry.objects.create(merchant=merchant, amount_paise=5000, entry_type="credit", description="Credit 2")
        LedgerEntry.objects.create(merchant=merchant, amount_paise=3000, entry_type="debit", description="Debit 1")

        from django.db.models import Sum
        total_credits = LedgerEntry.objects.filter(merchant=merchant, entry_type="credit").aggregate(total=Sum("amount_paise"))["total"]
        total_debits = LedgerEntry.objects.filter(merchant=merchant, entry_type="debit").aggregate(total=Sum("amount_paise"))["total"]

        expected_balance = total_credits - total_debits
        displayed_balance = merchant.get_available_balance()

        self.assertEqual(expected_balance, 12000)
        self.assertEqual(displayed_balance, 12000)
        self.assertEqual(expected_balance, displayed_balance)

        logger.info("Ledger invariant test passed - balance=%s", displayed_balance)
