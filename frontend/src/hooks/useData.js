import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../api/client";

// Generic polling hook - re-fetches every `intervalMs` milliseconds
export function usePolling(fetchFn, intervalMs = 4000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);

  const fetch = useCallback(async () => {
    try {
      const result = await fetchFn();
      setData(result.data);
      setError(null);
    } catch (err) {
      console.error("[usePolling] fetch error:", err.message);
      setError(err.response?.data?.error || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line

  useEffect(() => {
    setLoading(true);
    fetch();

    intervalRef.current = setInterval(fetch, intervalMs);
    console.log(`[usePolling] started polling every ${intervalMs}ms`);

    return () => {
      clearInterval(intervalRef.current);
      console.log("[usePolling] stopped polling");
    };
  }, [fetch, intervalMs]);

  return { data, loading, error, refetch: fetch };
}

// Dashboard data: balances + bank accounts
export function useDashboard(merchantId) {
  return usePolling(
    () => api.getDashboard(merchantId),
    4000,
    [merchantId]
  );
}

// Ledger entries with polling
export function useLedger(merchantId) {
  return usePolling(
    () => api.getLedger(merchantId),
    4000,
    [merchantId]
  );
}

// Payouts list with polling - allows live status updates
export function usePayouts(merchantId) {
  return usePolling(
    () => api.getPayouts(merchantId),
    3000,
    [merchantId]
  );
}

// Merchant list - fetched once, no polling needed
export function useMerchants() {
  const [merchants, setMerchants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getMerchants()
      .then((res) => {
        console.log("[useMerchants] loaded", res.data.length, "merchants");
        setMerchants(res.data);
      })
      .catch((err) => {
        console.error("[useMerchants] error:", err.message);
        setError("Could not load merchants");
      })
      .finally(() => setLoading(false));
  }, []);

  return { merchants, loading, error };
}
