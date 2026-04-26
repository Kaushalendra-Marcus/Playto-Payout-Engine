import { Skeleton } from "./Skeleton";

export function MerchantSelector({ merchants, selectedId, onSelect, loading }) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-14 w-full rounded-md" />
        ))}
      </div>
    );
  }

  if (!merchants || merchants.length === 0) {
    return (
      <p className="text-xs text-text-muted px-2">
        No merchants found. Run the seed script.
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {merchants.map((merchant) => {
        const isSelected = merchant.id === selectedId;
        return (
          <button
            key={merchant.id}
            onClick={() => {
              console.log("[MerchantSelector] selected merchant:", merchant.id);
              onSelect(merchant.id);
            }}
            className={`w-full text-left px-3 py-2.5 rounded-md transition-colors ${
              isSelected
                ? "bg-surface-3 border border-border text-text-primary"
                : "text-text-secondary hover:bg-surface-2 hover:text-text-primary border border-transparent"
            }`}
          >
            <p className="text-sm font-medium truncate">{merchant.name}</p>
            <p className="text-xs text-text-muted truncate">{merchant.email}</p>
          </button>
        );
      })}
    </div>
  );
}
