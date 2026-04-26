#  Run with: python manage.py shell < seed.py
#  Or: python manage.py runscript seed (if django-extensions installed)

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import logging
from payouts.models import Merchant, BankAccount, LedgerEntry, Payout, IdempotencyKey

logger = logging.getLogger(__name__)

print("Starting seed...")

if Merchant.objects.exists():
    print("Seed already done - skipping")
    import sys
    sys.exit(0)

IdempotencyKey.objects.all().delete()
Payout.objects.all().delete()
LedgerEntry.objects.all().delete()
BankAccount.objects.all().delete()
Merchant.objects.all().delete()

print("Cleared existing data")

#  Create Merchant 1
m1 = Merchant.objects.create(
    name="Kaushalendra Singh - Buildify Labs",
    email="yadavkausha4a5@gmail.com",
)
BankAccount.objects.create(
    merchant=m1,
    account_number="1234567890123456",
    ifsc_code="HDFC0001234",
    account_holder_name="Kaushalendra Singh",
    is_primary=True,
)
LedgerEntry.objects.create(merchant=m1, amount_paise=500000, entry_type="credit", description="Payment from client: Acme Corp (USD 600)")
LedgerEntry.objects.create(merchant=m1, amount_paise=250000, entry_type="credit", description="Payment from client: Globex LLC (USD 300)")
LedgerEntry.objects.create(merchant=m1, amount_paise=125000, entry_type="credit", description="Payment from client: Wayne Enterprises (USD 150)")
print(f"Created merchant: {m1.name} | Balance: Rs {m1.get_available_balance() / 100:.2f}")

#  Create Merchant 2
m2 = Merchant.objects.create(
    name="MKS Agencies Pvt Ltd",
    email="mks@priyaagencies.in",
)
BankAccount.objects.create(
    merchant=m2,
    account_number="9876543210987654",
    ifsc_code="ICIC0005678",
    account_holder_name="MKS Agencies Pvt Ltd",
    is_primary=True,
)
BankAccount.objects.create(
    merchant=m2,
    account_number="1111222233334444",
    ifsc_code="SBIN0009876",
    account_holder_name="MKS Agencies Pvt Ltd",
    is_primary=False,
)
LedgerEntry.objects.create(merchant=m2, amount_paise=1000000, entry_type="credit", description="Payment from client: TechCorp Inc (USD 1200)")
LedgerEntry.objects.create(merchant=m2, amount_paise=750000, entry_type="credit", description="Payment from client: StartupXYZ (USD 900)")
LedgerEntry.objects.create(merchant=m2, amount_paise=200000, entry_type="credit", description="Payment from client: FinanceHub (USD 240)")
LedgerEntry.objects.create(merchant=m2, amount_paise=500000, entry_type="debit", description="Payout to bank account 7654")
print(f"Created merchant: {m2.name} | Balance: Rs {m2.get_available_balance() / 100:.2f}")

#  Create Merchant 3
m3 = Merchant.objects.create(
    name="Sanhik - Playto",
    email="sanhik@goplayto.com",
)
BankAccount.objects.create(
    merchant=m3,
    account_number="5555666677778888",
    ifsc_code="AXIS0001111",
    account_holder_name="Sanhik",
    is_primary=True,
)
LedgerEntry.objects.create(merchant=m3, amount_paise=300000, entry_type="credit", description="Payment from client: MediaGroup (USD 360)")
LedgerEntry.objects.create(merchant=m3, amount_paise=180000, entry_type="credit", description="Payment from client: RetailCo (USD 216)")
LedgerEntry.objects.create(merchant=m3, amount_paise=420000, entry_type="credit", description="Payment from client: LogisticsPlus (USD 504)")
print(f"Created merchant: {m3.name} | Balance: Rs {m3.get_available_balance() / 100:.2f}")

print("")
print("Seed complete. Summary:")
for m in Merchant.objects.all():
    available = m.get_available_balance()
    print(f"  {m.name} | Available: Rs {available / 100:.2f} | Email: {m.email}")