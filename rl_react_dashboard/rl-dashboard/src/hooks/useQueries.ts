// ═══════════════════════════════════════════════════════════
// React Query Hooks — Server state management
// ═══════════════════════════════════════════════════════════
//
// Pattern: each hook wraps a single API concern
//   - useQuery for reads (cached, auto-refetched)
//   - useMutation for writes (with optimistic updates)
//
// Stale times tuned per data type:
//   - Market data: 5s (fast-changing)
//   - Profile: 5min (rarely changes)
//   - Agent status: 10s (moderate)

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, endpoints } from "../services/api";
import type {
  TradingProfile,
  AgentState,
  AgentCommand,
  PortfolioMetrics,
  Position,
  OHLCV,
  User,
} from "../types";

// ─── Auth Queries ─────────────────────────────────────────

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: async (): Promise<User> => {
      const { data } = await api.get(endpoints.auth.me);
      return data.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });
}

// ─── Profile Queries ──────────────────────────────────────

export function useTradingProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async (): Promise<TradingProfile> => {
      const { data } = await api.get(endpoints.profile.get);
      return data.data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (updates: Partial<TradingProfile>) => {
      const { data } = await api.patch(endpoints.profile.update, updates);
      return data.data as TradingProfile;
    },
    // Optimistic update
    onMutate: async (updates) => {
      await queryClient.cancelQueries({ queryKey: ["profile"] });
      const previous = queryClient.getQueryData<TradingProfile>(["profile"]);

      if (previous) {
        queryClient.setQueryData(["profile"], { ...previous, ...updates });
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(["profile"], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
    },
  });
}

// ─── Agent Queries ────────────────────────────────────────

export function useAgentStatus() {
  return useQuery({
    queryKey: ["agents", "status"],
    queryFn: async (): Promise<AgentState[]> => {
      const { data } = await api.get(endpoints.agents.status);
      return data.data;
    },
    staleTime: 10_000,
    refetchInterval: 15_000, // Poll every 15s as backup to WS
  });
}

export function useAgentControl() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (command: AgentCommand) => {
      const { data } = await api.post(endpoints.agents.control, command);
      return data.data;
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });
}

// ─── Portfolio Queries ────────────────────────────────────

export function usePortfolioMetrics() {
  return useQuery({
    queryKey: ["portfolio", "metrics"],
    queryFn: async (): Promise<PortfolioMetrics> => {
      const { data } = await api.get(endpoints.portfolio.metrics);
      return data.data;
    },
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}

export function usePositions() {
  return useQuery({
    queryKey: ["portfolio", "positions"],
    queryFn: async (): Promise<Position[]> => {
      const { data } = await api.get(endpoints.portfolio.positions);
      return data.data;
    },
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}

// ─── Market Data Queries ──────────────────────────────────

export function useMarketHistory(symbol: string, timeframe: string = "1D") {
  return useQuery({
    queryKey: ["market", "history", symbol, timeframe],
    queryFn: async (): Promise<OHLCV[]> => {
      const { data } = await api.get(endpoints.market.history(symbol), {
        params: { timeframe },
      });
      return data.data;
    },
    staleTime: 30_000,
    enabled: !!symbol,
  });
}
