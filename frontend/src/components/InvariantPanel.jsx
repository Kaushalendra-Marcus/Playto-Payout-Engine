import { useState } from "react";
import { api } from "../api/client";
import { formatPaise } from "../utils/format";

export function InvariantPanel({ merchantId }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function runCheck() {
    setLoading(true);
    setError(null);
    console.log("[InvariantPanel] running balance invariant check for:", merchantId);
    try {
      const res = await api.getInvariant(merchantId);
      setResult(res.data);
      console.log("[InvariantPanel] invariant check result:", res.data);
    } catch (err) {
      setError("Check failed");
      console.error("[InvariantPanel] error:", err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card p-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
        <h2 className="text-sm font-medium text-text-secondary uppercase tracking-widest">
          Ledger Invariant Check
        </h2>
        <button
          onClick={runCheck}
          disabled={loading}
          className="text-xs text-accent-blue hover:text-text-primary transition-colors disabled:opacity-40"
        >
          {loading ? "Checking..." : "Run Check"}
        </button>
      </div>

      <p className="text-xs text-text-muted mb-3">
        Verifies that sum(credits) - sum(debits) = displayed balance.
        This is the core money integrity invariant.
      </p>

      {error && (
        <p className="text-xs text-accent-red">{error}</p>
      )}

      {result && (
        <div className="space-y-2 animate-fade-in">
          {/* Pass/fail banner */}
          <div
            className={`rounded-md px-3 py-2 text-sm font-medium ${
              result.invariant_holds
                ? "bg-accent-green/10 text-accent-green border border-accent-green/20"
                : "bg-accent-red/10 text-accent-red border border-accent-red/20"
            }`}
          >
            {result.invariant_holds
              ? "Invariant holds - ledger is consistent"
              : "Invariant VIOLATED - ledger mismatch detected"}
          </div>

          {/* Breakdown table */}
          <div className="space-y-1 font-mono text-xs">
            <Row label="Total Credits" value={formatPaise(result.total_credits_paise)} positive />
            <Row label="Total Debits" value={formatPaise(result.total_debits_paise)} negative />
            <div className="border-t border-border pt-1 mt-1">
              <Row label="Calculated Balance" value={formatPaise(result.calculated_balance_paise)} />
              <Row label="Displayed Balance" value={formatPaise(result.displayed_balance_paise)} />
              <Row label="Held (Pending)" value={formatPaise(result.held_balance_paise)} />
              <Row label="Spendable" value={formatPaise(result.spendable_paise)} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, positive, negative }) {
  let color = "text-text-secondary";
  if (positive) color = "text-accent-green";
  if (negative) color = "text-accent-red";

  return (
    <div className="flex items-center justify-between py-0.5">
      <span className="text-text-muted">{label}</span>
      <span className={color}>{value}</span>
    </div>
  );
}
