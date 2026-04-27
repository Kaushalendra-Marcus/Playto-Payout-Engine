import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import { generateUUID, formatPaise } from "../utils/format";

export function PayoutForm({ merchantId, dashboard, onSuccess }) {
  const [amountRupees, setAmountRupees] = useState("");
  const [bankAccountId, setBankAccountId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  // A new idempotency key is generated per form session
  const [idempotencyKey, setIdempotencyKey] = useState(() => generateUUID());

  useEffect(() => {
    if (dashboard?.bank_accounts?.length > 0) {
      const primary = dashboard.bank_accounts.find((b) => b.is_primary);
      setBankAccountId(primary?.id || dashboard.bank_accounts[0].id);
      console.log("[PayoutForm] pre-selected bank account:", primary?.id);
    }
  }, [dashboard?.bank_accounts]);

  const spendable = dashboard
    ? dashboard.available_balance_paise - dashboard.held_balance_paise
    : 0;

  function handleAmountChange(e) {
    // Only allow positive numbers with up to 2 decimal places
    const val = e.target.value;
    if (val === "" || /^\d+(\.\d{0,2})?$/.test(val)) {
      setAmountRupees(val);
    }
  }

  async function handleSubmit() {
    const rupees = parseFloat(amountRupees);
    if (!rupees || rupees <= 0) {
      toast.error("Enter a valid amount");
      return;
    }
    if (!bankAccountId) {
      toast.error("Select a bank account");
      return;
    }

    // Convert rupees to paise - always integer math, never float storage
    const amountPaise = Math.round(rupees * 100);

    if (amountPaise > spendable) {
      toast.error(
        `Insufficient balance. Spendable: ${formatPaise(spendable)}`
      );
      return;
    }

    setSubmitting(true);
    console.log(
      "[PayoutForm] submitting payout - amount_paise=%d key=%s",
      amountPaise,
      idempotencyKey
    );

    try {
      await api.createPayout(
        merchantId,
        { amount_paise: amountPaise, bank_account_id: bankAccountId },
        idempotencyKey
      );
      toast.success("Payout request submitted");
      setAmountRupees("");
      // Regenerate key so the next submission is a new request
      setIdempotencyKey(generateUUID());
      console.log("[PayoutForm] payout created successfully");
      onSuccess?.();
    } catch (err) {
      const msg = err.response?.data?.error || "Payout request failed";
      console.error("[PayoutForm] payout error:", msg);
      toast.error(msg);
      // Do NOT regenerate the key on error - same key allows safe retry
    } finally {
      setSubmitting(false);
    }
  }

  const bankAccounts = dashboard?.bank_accounts || [];

  return (
    <div className="card p-5">
      <h2 className="text-sm font-medium text-text-secondary uppercase tracking-widest mb-4">
        Request Payout
      </h2>

      {/* Amount input */}
      <div className="mb-3">
        <label className="block text-xs text-text-secondary mb-1">
          Amount (INR)
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm font-mono">
            Rs
          </span>
          <input
            type="text"
            inputMode="decimal"
            value={amountRupees}
            onChange={handleAmountChange}
            placeholder="0.00"
            disabled={submitting}
            className="w-full bg-surface-2 border border-border rounded-md pl-9 pr-3 py-2.5 text-sm font-mono text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-blue transition-colors disabled:opacity-50"
          />
        </div>
        {amountRupees && (
          <p className="text-xs text-text-muted mt-1 font-mono">
            = {Math.round(parseFloat(amountRupees || 0) * 100)} paise
          </p>
        )}
      </div>

      {/* Bank account selector */}
      <div className="mb-4">
        <label className="block text-xs text-text-secondary mb-1">
          Bank Account
        </label>
        {bankAccounts.length === 0 ? (
          <p className="text-xs text-text-muted">No bank accounts found</p>
        ) : (
          <select
            value={bankAccountId}
            onChange={(e) => setBankAccountId(e.target.value)}
            disabled={submitting}
            className="w-full bg-surface-2 border border-border rounded-md px-3 py-2.5 text-sm text-text-primary focus:outline-none focus:border-accent-blue transition-colors disabled:opacity-50"
          >
            {bankAccounts.map((ba) => (
              <option key={ba.id} value={ba.id}>
                {ba.account_holder_name} - {ba.masked_account_number}{" "}
                ({ba.ifsc_code})
                {ba.is_primary ? " - Primary" : ""}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Spendable balance hint */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs text-text-muted">Spendable balance</span>
        <span className="text-xs font-mono text-accent-green">
          {formatPaise(spendable)}
        </span>
      </div>

      {/* Idempotency key display */}
      <div className="mb-4 bg-surface-2 rounded-md px-3 py-2 border border-border">
        <p className="text-xs text-text-muted mb-0.5">Idempotency Key</p>
        <p className="text-xs font-mono text-text-secondary truncate">{idempotencyKey}</p>
      </div>

      <button
        onClick={handleSubmit}
        disabled={submitting || !amountRupees || !bankAccountId}
        className="w-full bg-accent-green text-surface-0 font-medium text-sm py-2.5 rounded-md transition-opacity hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        {submitting ? "Submitting..." : "Submit Payout"}
      </button>
    </div>
  );
}
