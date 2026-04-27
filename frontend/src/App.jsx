import { useState, useEffect } from "react";
import { MerchantSelector } from "./components/MerchantSelector";
import { DashboardPage } from "./pages/DashboardPage";
import { useMerchants } from "./hooks/useData";

export default function App() {
  const { merchants, loading, error } = useMerchants();
  const [selectedMerchantId, setSelectedMerchantId] = useState(null);

  // Auto-select first merchant when list loads
  useEffect(() => {
    if (merchants.length > 0 && !selectedMerchantId) {
      console.log("[App] auto-selecting first merchant:", merchants[0].id);
      setSelectedMerchantId(merchants[0].id);
    }
  }, [merchants, selectedMerchantId]);

  const selectedMerchant = merchants.find((m) => m.id === selectedMerchantId);

  return (
    <div className="min-h-screen bg-surface-0 flex flex-col">
      {/* Top nav */}
      <header className="border-b border-border bg-surface-1 px-4 sm:px-6 py-4 flex flex-wrap items-center gap-2 sm:gap-4">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded bg-accent-green flex items-center justify-center">
            <span className="text-surface-0 text-xs font-bold">P</span>
          </div>
          <span className="text-text-primary font-semibold text-sm tracking-tight">
            Playto Pay
          </span>
        </div>
        <span className="hidden sm:inline text-border">|</span>
        <span className="text-text-muted text-xs">Payout Engine</span>

        {/* Live indicator */}
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse-dot" />
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row overflow-hidden">
        {/* Sidebar */}
        <aside className="w-full lg:w-56 shrink-0 border-b lg:border-b-0 lg:border-r border-border bg-surface-1 p-4 overflow-y-auto">
          <p className="text-xs font-medium text-text-muted uppercase tracking-widest mb-3 px-2">
            Merchants
          </p>
          {error ? (
            <p className="text-xs text-accent-red px-2">{error}</p>
          ) : (
            <MerchantSelector
              merchants={merchants}
              selectedId={selectedMerchantId}
              onSelect={setSelectedMerchantId}
              loading={loading}
            />
          )}
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          {!selectedMerchantId ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-text-muted text-sm">
                Select a merchant from the sidebar
              </p>
            </div>
          ) : (
            <DashboardPage
              key={selectedMerchantId}
              merchantId={selectedMerchantId}
              merchantName={selectedMerchant?.name || ""}
            />
          )}
        </main>
      </div>
    </div>
  );
}
