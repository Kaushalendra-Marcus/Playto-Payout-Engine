import { statusClass, statusLabel } from "../utils/format";

// Live dot shown next to processing status to indicate active work
function LiveDot() {
  return (
    <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-blue animate-pulse-dot mr-1.5" />
  );
}

export function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-mono font-medium ${statusClass(status)}`}
    >
      {status === "processing" && <LiveDot />}
      {statusLabel(status)}
    </span>
  );
}
