// ═══════════════════════════════════════════════════════════
// API Client — Axios instance with JWT interceptors
// ═══════════════════════════════════════════════════════════
//
// Token flow:
//   1. Access token sent via Authorization header
//   2. On 401, interceptor attempts silent refresh
//   3. If refresh fails, user is logged out
//   4. Refresh token stored in HTTP-only cookie (set by server)
//   5. Access token stored in memory only (Zustand store)
//
// This avoids XSS exposure of tokens in localStorage.

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// ─── Axios Instance ───────────────────────────────────────

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 15_000,
  withCredentials: true, // Send HTTP-only cookies for refresh token
  headers: {
    "Content-Type": "application/json",
  },
});

// ─── Token Management ─────────────────────────────────────
// Access token lives in memory only — never in localStorage

let accessToken: string | null = null;
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: Error) => void;
}> = [];

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

function processQueue(error: Error | null, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
}

// ─── Request Interceptor ──────────────────────────────────
// Attach access token to every request

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response Interceptor ─────────────────────────────────
// On 401: attempt token refresh, then retry original request
// Uses a queue to batch concurrent 401s into a single refresh

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Only handle 401 (unauthorized) and only retry once
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Another refresh is in progress — queue this request
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${token}`;
        }
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Refresh endpoint uses HTTP-only cookie (withCredentials: true)
      const { data } = await axios.post(
        `${API_BASE}/auth/refresh`,
        {},
        { withCredentials: true }
      );

      const newToken = data.data.accessToken;
      setAccessToken(newToken);
      processQueue(null, newToken);

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
      }
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError as Error, null);
      setAccessToken(null);
      // Redirect to login — the auth store listener handles this
      window.dispatchEvent(new CustomEvent("auth:logout"));
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

// ─── API Endpoints ────────────────────────────────────────

export const endpoints = {
  auth: {
    login: "/auth/login",
    signup: "/auth/signup",
    refresh: "/auth/refresh",
    logout: "/auth/logout",
    me: "/auth/me",
  },
  profile: {
    get: "/profile",
    update: "/profile",
    list: "/profile/list",
  },
  agents: {
    status: "/agents/status",
    control: "/agents/control",
    models: "/agents/models",
    history: "/agents/history",
  },
  market: {
    symbols: "/market/symbols",
    history: (symbol: string) => `/market/history/${symbol}`,
    regime: "/market/regime",
  },
  portfolio: {
    metrics: "/portfolio/metrics",
    positions: "/portfolio/positions",
    trades: "/portfolio/trades",
  },
} as const;
