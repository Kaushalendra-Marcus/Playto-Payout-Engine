import { useCallback } from "react";
import { BalanceCards } from "../components/BalanceCards";
import { PayoutForm } from "../components/PayoutForm";
import { PayoutsTable } from "../components/PayoutsTable";
import { LedgerTable } from "../components/LedgerTable";
import { InvariantPanel } from "../components/InvariantPanel";
import { useDashboard, useLedger, usePayouts } from "../hooks/useData";

export function DashboardPage({ merchantId, merchantName }) {
  const {
    data: dashboard,
    loading: dashLoading,
    refetch: refetchDashboard,
  } = useDashboard(merchantId);

  const {
    data: ledger,
    loading: ledgerLoading,
    refetch: refetchLedger,
  } = useLedger(merchantId);

  const {
    data: payouts,
    loading: payoutsLoading,
    refetch: refetchPayouts,
  } = usePayouts(merchantId);

  // After a successful payout submission, immediately refetch all data
  const handlePayoutSuccess = useCallback(() => {
    console.log("[DashboardPage] payout submitted - refreshing all data");
    refetchDashboard();
    refetchLedger();
    refetchPayouts();
  }, [refetchDashboard, refetchLedger, refetchPayouts]);

  return (
    <div className="animate-fade-in min-w-0">
      {/* Merchant header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">
          {merchantName}
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          Merchant ID: <span className="font-mono">{merchantId}</span>
        </p>
      </div>

      {/* Balance overview */}
      <BalanceCards dashboard={dashboard} loading={dashLoading} />

      {/* Main content: form + invariant check on left, tables on right */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left column - actions */}
        <div className="space-y-4">
          <PayoutForm
            merchantId={merchantId}
            dashboard={dashboard}
            onSuccess={handlePayoutSuccess}
          />
          <InvariantPanel merchantId={merchantId} />
        </div>

        {/* Right column - data tables */}
        <div className="xl:col-span-2 space-y-6 min-w-0">
          <PayoutsTable payouts={payouts} loading={payoutsLoading} />
          <LedgerTable entries={ledger} loading={ledgerLoading} />
        </div>
      </div>
    </div>
  );
}
