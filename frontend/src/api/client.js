import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

const client = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Log every request and response for debugging
client.interceptors.request.use((config) => {
  console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data || "");
  return config;
});

client.interceptors.response.use(
  (response) => {
    console.log(`[API] ${response.status} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url;
    const data = error.response?.data;
    console.error(`[API] ERROR ${status} ${url}`, data);
    return Promise.reject(error);
  }
);

export const api = {
  getMerchants: () => client.get("/merchants/"),

  getDashboard: (merchantId) => client.get(`/merchants/${merchantId}/`),

  getLedger: (merchantId) => client.get(`/merchants/${merchantId}/ledger/`),

  getPayouts: (merchantId) => client.get(`/merchants/${merchantId}/payouts/`),

  getPayout: (merchantId, payoutId) =>
    client.get(`/merchants/${merchantId}/payouts/${payoutId}/`),

  createPayout: (merchantId, body, idempotencyKey) =>
    client.post(`/merchants/${merchantId}/payouts/`, body, {
      headers: { "Idempotency-Key": idempotencyKey },
    }),

  getInvariant: (merchantId) => client.get(`/merchants/${merchantId}/invariant/`),
};
