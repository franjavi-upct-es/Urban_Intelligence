// frontend/src/api/client.ts
// Urban Intelligence Framework v2.0.0
// Axios API client with base URL and error handling

import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/** Pre-configured Axios instance for all API calls. */
export const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// —— Response interceptor: normalise errors ——————————————————————————————————
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      "Unknown error";
    return Promise.reject(new Error(message));
  },
);

/** WebSocket base URL derived from the API base URL. */
export const WS_BASE_URL = (import.meta.env.VITE_WS_URL ?? BASE_URL).replace(
  /^http/,
  "ws",
);
