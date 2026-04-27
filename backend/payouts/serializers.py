import logging
from rest_framework import serializers
from .models import Merchant, LedgerEntry, Payout, BankAccount

logger = logging.getLogger(__name__)


class BankAccountSerializer(serializers.ModelSerializer):
    #  Mask account number except last 4 digits for security
    masked_account_number = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = ["id", "account_holder_name", "ifsc_code", "masked_account_number", "is_primary"]

    def get_masked_account_number(self, obj):
        return "XXXX" + obj.account_number[-4:]


class LedgerEntrySerializer(serializers.ModelSerializer):
    #  Returning amount in paise and also rupees for display convenience
    amount_rupees = serializers.SerializerMethodField()

    class Meta:
        model = LedgerEntry
        fields = [
            "id", "entry_type", "amount_paise", "amount_rupees",
            "description", "payout_id", "created_at"
        ]

    def get_amount_rupees(self, obj):
        # divide by 100 to convert paise to rupees for display only
        return obj.amount_paise / 100


class PayoutSerializer(serializers.ModelSerializer):
    amount_rupees = serializers.SerializerMethodField()
    bank_account = BankAccountSerializer(read_only=True)

    class Meta:
        model = Payout
        fields = [
            "id", "amount_paise", "amount_rupees", "status",
            "bank_account", "attempt_count", "failure_reason",
            "created_at", "updated_at"
        ]

    def get_amount_rupees(self, obj):
        return obj.amount_paise / 100


class CreatePayoutSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=100)  # minimum 1 rupee = 100 paise
    bank_account_id = serializers.UUIDField()

    def validate_amount_paise(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be a positive integer in paise.")
        return value

    def validate_bank_account_id(self, value):
        #  Validate bank account exists - merchant scoping done in view
        if not BankAccount.objects.filter(id=value).exists():
            raise serializers.ValidationError("Bank account not found.")
        return value


class MerchantDashboardSerializer(serializers.ModelSerializer):
    available_balance_paise = serializers.SerializerMethodField()
    available_balance_rupees = serializers.SerializerMethodField()
    held_balance_paise = serializers.SerializerMethodField()
    held_balance_rupees = serializers.SerializerMethodField()
    total_credits_paise = serializers.SerializerMethodField()
    total_debits_paise = serializers.SerializerMethodField()
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Merchant
        fields = [
            "id", "name", "email",
            "available_balance_paise", "available_balance_rupees",
            "held_balance_paise", "held_balance_rupees",
            "total_credits_paise", "total_debits_paise",
            "bank_accounts"
        ]

    def get_available_balance_paise(self, obj):
        return obj.get_available_balance()

    def get_available_balance_rupees(self, obj):
        return obj.get_available_balance() / 100

    def get_held_balance_paise(self, obj):
        return obj.get_held_balance()

    def get_held_balance_rupees(self, obj):
        return obj.get_held_balance() / 100

    def get_total_credits_paise(self, obj):
        from django.db.models import Sum
        result = obj.ledger_entries.filter(entry_type=LedgerEntry.CREDIT).aggregate(
            total=Sum("amount_paise")
        )
        return result["total"] or 0

    def get_total_debits_paise(self, obj):
        from django.db.models import Sum
        result = obj.ledger_entries.filter(entry_type=LedgerEntry.DEBIT).aggregate(
            total=Sum("amount_paise")
        )
        return result["total"] or 0
