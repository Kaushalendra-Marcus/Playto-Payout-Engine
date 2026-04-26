// Generic skeleton placeholder shown while data is loading
export function Skeleton({ className = "" }) {
  return <div className={`skeleton ${className}`} />;
}

// Skeleton layout matching the balance cards
export function BalanceSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {[0, 1, 2].map((i) => (
        <div key={i} className="card p-5">
          <Skeleton className="h-3 w-24 mb-3" />
          <Skeleton className="h-7 w-36" />
        </div>
      ))}
    </div>
  );
}

// Skeleton for table rows
export function TableRowSkeleton({ cols = 4 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <Skeleton className="h-3 w-full" />
        </td>
      ))}
    </tr>
  );
}
