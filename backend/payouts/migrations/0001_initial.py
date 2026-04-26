import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Merchant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_accounts", to="payouts.merchant")),
                ("account_number", models.CharField(max_length=20)),
                ("ifsc_code", models.CharField(max_length=11)),
                ("account_holder_name", models.CharField(max_length=255)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-is_primary", "created_at"]},
        ),
        migrations.CreateModel(
            name="Payout",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payouts", to="payouts.merchant")),
                ("bank_account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payouts", to="payouts.bankaccount")),
                ("amount_paise", models.BigIntegerField()),
                ("status", models.CharField(
                    choices=[("pending", "Pending"), ("processing", "Processing"), ("completed", "Completed"), ("failed", "Failed")],
                    default="pending",
                    max_length=20,
                )),
                ("attempt_count", models.IntegerField(default=0)),
                ("last_attempted_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="LedgerEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="payouts.merchant")),
                ("amount_paise", models.BigIntegerField()),
                ("entry_type", models.CharField(choices=[("credit", "Credit"), ("debit", "Debit")], max_length=10)),
                ("description", models.CharField(max_length=500)),
                ("payout", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="ledger_entries", to="payouts.payout")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="IdempotencyKey",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("merchant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="idempotency_keys", to="payouts.merchant")),
                ("key", models.CharField(max_length=255)),
                ("response_status_code", models.IntegerField(blank=True, null=True)),
                ("response_body", models.JSONField(blank=True, null=True)),
                ("payout", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="idempotency_key", to="payouts.payout")),
                ("is_complete", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
            ],
        ),
        migrations.AddIndex(
            model_name="ledgerentry",
            index=models.Index(fields=["merchant", "-created_at"], name="payouts_led_merchan_idx"),
        ),
        migrations.AddIndex(
            model_name="ledgerentry",
            index=models.Index(fields=["merchant", "entry_type"], name="payouts_led_type_idx"),
        ),
        migrations.AddIndex(
            model_name="payout",
            index=models.Index(fields=["merchant", "-created_at"], name="payouts_pay_merchan_idx"),
        ),
        migrations.AddIndex(
            model_name="payout",
            index=models.Index(fields=["status", "created_at"], name="payouts_pay_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payout",
            index=models.Index(fields=["status", "last_attempted_at"], name="payouts_pay_stuck_idx"),
        ),
        migrations.AddIndex(
            model_name="idempotencykey",
            index=models.Index(fields=["merchant", "key"], name="payouts_idem_key_idx"),
        ),
        migrations.AddIndex(
            model_name="idempotencykey",
            index=models.Index(fields=["expires_at"], name="payouts_idem_exp_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="idempotencykey",
            unique_together={("merchant", "key")},
        ),
    ]
