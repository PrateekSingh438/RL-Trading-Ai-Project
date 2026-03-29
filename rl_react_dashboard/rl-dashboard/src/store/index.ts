// ═══════════════════════════════════════════════════════════
// Zustand Stores — Auth + UI global state
// ═══════════════════════════════════════════════════════════
//
// Why Zustand over Context:
//   - No re-render cascades (selector-based subscriptions)
//   - Works outside React (interceptors, WS handlers)
//   - Simpler than Redux, more powerful than Context
//
// Server state (portfolio, market data) → TanStack Query
// Client state (auth, UI toggles, theme) → Zustand

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, TradingProfile, AgentState, TradingMode } from "../types";

// ─── Auth Store ───────────────────────────────────────────

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) =>
    set({ user, isAuthenticated: !!user, isLoading: false }),

  setLoading: (isLoading) => set({ isLoading }),

  logout: () =>
    set({ user: null, isAuthenticated: false, isLoading: false }),
}));

// ─── UI Store ─────────────────────────────────────────────

type Theme = "light" | "dark" | "system";
type SidebarTab = "overview" | "agents" | "logs" | "settings";

interface UIState {
  theme: Theme;
  sidebarOpen: boolean;
  activeTab: SidebarTab;
  chartSymbol: string;
  logFilter: "ALL" | "INFO" | "WARN" | "ERROR";

  setTheme: (theme: Theme) => void;
  toggleSidebar: () => void;
  setActiveTab: (tab: SidebarTab) => void;
  setChartSymbol: (symbol: string) => void;
  setLogFilter: (filter: "ALL" | "INFO" | "WARN" | "ERROR") => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: "dark",
      sidebarOpen: true,
      activeTab: "overview",
      chartSymbol: "AAPL",
      logFilter: "ALL",

      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setActiveTab: (activeTab) => set({ activeTab }),
      setChartSymbol: (chartSymbol) => set({ chartSymbol }),
      setLogFilter: (logFilter) => set({ logFilter }),
    }),
    {
      name: "rl-trader-ui",       // localStorage key
      partialize: (state) => ({   // Only persist these fields
        theme: state.theme,
        sidebarOpen: state.sidebarOpen,
        chartSymbol: state.chartSymbol,
      }),
    }
  )
);

// ─── Trading Profile Store ────────────────────────────────

interface ProfileState {
  activeProfile: TradingProfile | null;
  setProfile: (profile: TradingProfile | null) => void;
  updateProfile: (updates: Partial<TradingProfile>) => void;
}

export const useProfileStore = create<ProfileState>()((set) => ({
  activeProfile: null,

  setProfile: (activeProfile) => set({ activeProfile }),

  updateProfile: (updates) =>
    set((state) => ({
      activeProfile: state.activeProfile
        ? { ...state.activeProfile, ...updates }
        : null,
    })),
}));

// ─── Agent Store ──────────────────────────────────────────

interface AgentStoreState {
  agents: AgentState[];
  activeAgentId: string | null;

  setAgents: (agents: AgentState[]) => void;
  updateAgent: (id: string, updates: Partial<AgentState>) => void;
  setActiveAgent: (id: string | null) => void;
}

export const useAgentStore = create<AgentStoreState>()((set) => ({
  agents: [],
  activeAgentId: null,

  setAgents: (agents) => set({ agents }),

  updateAgent: (id, updates) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      ),
    })),

  setActiveAgent: (activeAgentId) => set({ activeAgentId }),
}));

// ─── Notification Store ───────────────────────────────────

export interface AppNotification {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
  timestamp: number;
}

interface NotificationState {
  notifications: AppNotification[];
  push: (n: Omit<AppNotification, "id" | "timestamp">) => void;
  dismiss: (id: string) => void;
}

export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],
  push: (n) =>
    set((state) => ({
      notifications: [
        {
          ...n,
          id: Math.random().toString(36).slice(2, 10),
          timestamp: Date.now(),
        },
        ...state.notifications,
      ].slice(0, 5),
    })),
  dismiss: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
}));
