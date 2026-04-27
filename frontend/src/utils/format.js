// Always takeing paise as input, never rupees
export function formatPaise(paise) {
  if (paise == null) return "Rs 0.00";
  const rupees = paise / 100;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(rupees);
}

//Format ISO date string to a readable local time
export function formatDate(isoString) {
  if (!isoString) return "-";
  return new Date(isoString).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

// Format ISO date string to relative time (e.g. "2 min ago")
export function timeAgo(isoString) {
  if (!isoString) return "";
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return formatDate(isoString);
}

// Generate a UUID v4 for idempotency keys
export function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Map payout status string to Tailwind class
export function statusClass(status) {
  const map = {
    pending: "tag-pending",
    processing: "tag-processing",
    completed: "tag-completed",
    failed: "tag-failed",
  };
  return map[status] || "bg-surface-3 text-text-secondary";
}

// Map payout status to display label
export function statusLabel(status) {
  const map = {
    pending: "Pending",
    processing: "Processing",
    completed: "Completed",
    failed: "Failed",
  };
  return map[status] || status;
}
