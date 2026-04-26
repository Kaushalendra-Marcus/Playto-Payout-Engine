import { TableRowSkeleton } from "./Skeleton";
import { formatPaise, timeAgo, formatDate } from "../utils/format";

function EntryTypeTag({ type }) {
  if (type === "credit") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-mono font-medium text-accent-green">
        <span>+</span> Credit
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-mono font-medium text-accent-red">
      <span>-</span> Debit
    </span>
  );
}

export function LedgerTable({ entries, loading }) {
  if (loading) {
    return (
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <h2 className="text-sm font-medium text-text-secondary uppercase tracking-widest">
            Ledger
          </h2>
        </div>
        <table className="w-full">
          <thead>
            <LedgerTableHead />
          </thead>
          <tbody>
            {[0, 1, 2, 4].map((i) => (
              <TableRowSkeleton key={i} cols={4} />
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-secondary uppercase tracking-widest">
          Ledger
        </h2>
        <span className="text-xs text-text-muted">
          {entries?.length || 0} entries - immutable
        </span>
      </div>

      {!entries || entries.length === 0 ? (
        <div className="px-5 py-10 text-center">
          <p className="text-text-muted text-sm">No ledger entries</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <LedgerTableHead />
            </thead>
            <tbody>
              {entries.map((entry) => (
                <LedgerRow key={entry.id} entry={entry} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LedgerTableHead() {
  return (
    <tr className="border-b border-border">
      {["Type", "Amount", "Description", "Time"].map((h) => (
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

function LedgerRow({ entry }) {
  const isCredit = entry.entry_type === "credit";

  return (
    <tr className="border-b border-border last:border-0 hover:bg-surface-2 transition-colors animate-fade-in">
      <td className="px-4 py-3">
        <EntryTypeTag type={entry.entry_type} />
      </td>
      <td className="px-4 py-3">
        <span
          className={`font-mono text-sm font-medium ${
            isCredit ? "text-accent-green" : "text-accent-red"
          }`}
        >
          {isCredit ? "+" : "-"}{formatPaise(entry.amount_paise)}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className="text-xs text-text-secondary max-w-xs block truncate">
          {entry.description}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className="text-xs text-text-muted"
          title={formatDate(entry.created_at)}
        >
          {timeAgo(entry.created_at)}
        </span>
      </td>
    </tr>
  );
}
