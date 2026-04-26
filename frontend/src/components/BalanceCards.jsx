import { formatPaise } from "../utils/format";
import { BalanceSkeleton } from "./Skeleton";

function BalanceCard({ label, amount, accent, note }) {
  const accentColors = {
    green: "text-accent-green",
    amber: "text-accent-amber",
    blue: "text-accent-blue",
  };

  return (
    <div className="card p-5 animate-fade-in">
      <p className="text-text-secondary text-xs font-medium uppercase tracking-widest mb-2">
        {label}
      </p>
      <p className={`text-2xl font-semibold font-mono ${accentColors[accent] || "text-text-primary"}`}>
        {formatPaise(amount)}
      </p>
      {note && (
        <p className="text-text-muted text-xs mt-1.5">{note}</p>
      )}
    </div>
  );
}

export function BalanceCards({ dashboard, loading }) {
  if (loading || !dashboard) return <BalanceSkeleton />;

  const available = dashboard.available_balance_paise;
  const held = dashboard.held_balance_paise;
  const spendable = available - held;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <BalanceCard
        label="Spendable Balance"
        amount={spendable}
        accent="green"
        note="Available minus held funds"
      />
      <BalanceCard
        label="Held Balance"
        amount={held}
        accent="amber"
        note="Reserved for pending payouts"
      />
      <BalanceCard
        label="Total Ledger Balance"
        amount={available}
        accent="blue"
        note="Sum of all credits minus debits"
      />
    </div>
  );
}
