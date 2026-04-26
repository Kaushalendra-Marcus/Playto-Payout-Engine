#  Run with: python manage.py shell < seed.py
#  Or: python manage.py runscript seed (if django-extensions installed)

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import logging
from payouts.models import Merchant, BankAccount, LedgerEntry

logger = logging.getLogger(__name__)

print("Starting seed...")

#  Clear existing data
LedgerEntry.objects.all().delete()
BankAccount.objects.all().delete()
Merchant.objects.all().delete()

print("Cleared existing data")

#  Create Merchant 1 - a freelance designer
m1 = Merchant.objects.create(
    name="Arjun Sharma - Design Studio",
    email="arjun@designstudio.in",
)
BankAccount.objects.create(
    merchant=m1,
    account_number="1234567890123456",
    ifsc_code="HDFC0001234",
    account_holder_name="Arjun Sharma",
    is_primary=True,
)
#  Seed credits: simulated customer payments from international clients
LedgerEntry.objects.create(merchant=m1, amount_paise=500000, entry_type="credit", description="Payment from client: Acme Corp (USD 600)")
LedgerEntry.objects.create(merchant=m1, amount_paise=250000, entry_type="credit", description="Payment from client: Globex LLC (USD 300)")
LedgerEntry.objects.create(merchant=m1, amount_paise=125000, entry_type="credit", description="Payment from client: Wayne Enterprises (USD 150)")
print(f"Created merchant: {m1.name} | Balance: Rs {m1.get_available_balance() / 100:.2f}")

#  Create Merchant 2 - a digital marketing agency
m2 = Merchant.objects.create(
    name="Priya Agencies Pvt Ltd",
    email="priya@priyaagencies.in",
)
BankAccount.objects.create(
    merchant=m2,
    account_number="9876543210987654",
    ifsc_code="ICIC0005678",
    account_holder_name="Priya Nair",
    is_primary=True,
)
BankAccount.objects.create(
    merchant=m2,
    account_number="1111222233334444",
    ifsc_code="SBIN0009876",
    account_holder_name="Priya Agencies Pvt Ltd",
    is_primary=False,
)
LedgerEntry.objects.create(merchant=m2, amount_paise=1000000, entry_type="credit", description="Payment from client: TechCorp Inc (USD 1200)")
LedgerEntry.objects.create(merchant=m2, amount_paise=750000, entry_type="credit", description="Payment from client: StartupXYZ (USD 900)")
LedgerEntry.objects.create(merchant=m2, amount_paise=200000, entry_type="credit", description="Payment from client: FinanceHub (USD 240)")
#  Merchant 2 has already received one successful payout
LedgerEntry.objects.create(merchant=m2, amount_paise=500000, entry_type="debit", description="Payout to bank account 7654")
print(f"Created merchant: {m2.name} | Balance: Rs {m2.get_available_balance() / 100:.2f}")

#  Create Merchant 3 - a SaaS developer
m3 = Merchant.objects.create(
    name="Kiran Dev - SaaS Solutions",
    email="kiran@kirandev.io",
)
BankAccount.objects.create(
    merchant=m3,
    account_number="5555666677778888",
    ifsc_code="AXIS0001111",
    account_holder_name="Kiran Dev",
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
