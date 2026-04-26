import { StatusBadge } from "./StatusBadge";
import { TableRowSkeleton } from "./Skeleton";
import { formatPaise, formatDate, timeAgo } from "../utils/format";

export function PayoutsTable({ payouts, loading }) {
  if (loading) {
    return (
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-sm font-medium text-text-secondary uppercase tracking-widest">
            Payout History
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px]">
            <thead>
              <TableHead />
            </thead>
            <tbody>
              {[0, 1, 2].map((i) => (
                <TableRowSkeleton key={i} cols={5} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-4 sm:px-5 py-4 border-b border-border flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-text-secondary uppercase tracking-widest">
          Payout History
        </h2>
        <span className="text-xs text-text-muted">
          {payouts?.length || 0} records - live
        </span>
      </div>

      {!payouts || payouts.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <p className="text-text-muted text-sm">No payouts yet</p>
          <p className="text-text-muted text-xs mt-1">
            Submit a payout request to see it here
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px]">
            <thead>
              <TableHead />
            </thead>
            <tbody>
              {payouts.map((payout) => (
                <PayoutRow key={payout.id} payout={payout} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TableHead() {
  return (
    <tr className="border-b border-border">
      {["Payout ID", "Amount", "Bank Account", "Status", "Created"].map((h) => (
        <th
          key={h}
          className="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider"
        >
          {h}
        </th>
      ))}
    </tr>
  );
}

function PayoutRow({ payout }) {
  return (
    <tr className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors animate-fade-in">
      <td className="px-4 py-3">
        <span className="font-mono text-xs text-text-secondary">
          {payout.id.slice(0, 8)}...
        </span>
      </td>
      <td className="px-4 py-3">
        <span className="font-mono text-sm text-text-primary">
          {formatPaise(payout.amount_paise)}
        </span>
      </td>
      <td className="px-4 py-3">
        <div>
          <span className="text-xs text-text-primary">
            {payout.bank_account?.account_holder_name}
          </span>
          <span className="block text-xs font-mono text-text-muted">
            {payout.bank_account?.masked_account_number} -{" "}
            {payout.bank_account?.ifsc_code}
          </span>
        </div>
      </td>
      <td className="px-4 py-3">
        <div>
          <StatusBadge status={payout.status} />
          {payout.failure_reason && (
            <p className="text-xs text-accent-red mt-1 max-w-xs truncate">
              {payout.failure_reason}
            </p>
          )}
          {payout.attempt_count > 0 && payout.status !== "completed" && (
            <p className="text-xs text-text-muted mt-0.5">
              Attempt {payout.attempt_count}
            </p>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <span
          className="text-xs text-text-muted"
          title={formatDate(payout.created_at)}
        >
          {timeAgo(payout.created_at)}
        </span>
      </td>
    </tr>
  );
}
