# RL Trading Dashboard — Architecture & Documentation

## A. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER (React + Vite)                   │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │  Zustand  │  │  React   │  │   Axios   │  │  WebSocket   │  │
│  │  Stores   │  │  Query   │  │  Client   │  │  Client      │  │
│  │ (auth/ui) │  │ (server) │  │ (REST)    │  │ (streaming)  │  │
│  └─────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
│        │              │              │               │          │
└────────┼──────────────┼──────────────┼───────────────┼──────────┘
         │              │              │               │
─────────┼──────────────┼──────────────┼───────────────┼──────────
         │              │              │               │
┌────────┼──────────────┼──────────────┼───────────────┼──────────┐
│        ▼              ▼              ▼               ▼          │
│                    FastAPI Backend                               │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │  Auth    │  │  REST    │  │  WS       │  │  Task Queue  │  │
│  │  (JWT)   │  │  Routes  │  │  Manager  │  │  (Celery)    │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
│       │              │              │               │          │
│       ▼              ▼              ▼               ▼          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    RL Trading Engine                     │   │
│  │                                                         │   │
│  │  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌───────────┐  │   │
│  │  │  PPO    │  │  SAC    │  │ Risk   │  │ Regime    │  │   │
│  │  │  Agent  │  │  Agent  │  │ Mgmt   │  │ Detector  │  │   │
│  │  └────┬────┘  └────┬────┘  └───┬────┘  └─────┬─────┘  │   │
│  │       └──────┬─────┘           │              │        │   │
│  │              ▼                 ▼              ▼        │   │
│  │       ┌─────────────┐  ┌───────────┐  ┌───────────┐   │   │
│  │       │  Ensemble   │  │ Sentiment │  │ Explainer │   │   │
│  │       │  Agent      │  │ Validator │  │           │   │   │
│  │       └─────────────┘  └───────────┘  └───────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐                    │
│  │ Postgres │  │  Redis   │  │  yfinance  │                    │
│  │ (users)  │  │ (cache)  │  │ (market)   │                    │
│  └──────────┘  └──────────┘  └───────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### REST (request/response):
```
Login        → POST /auth/login      → JWT tokens
Profile      → GET  /profile         → TradingProfile
Agent ctrl   → POST /agents/control  → { action: "start", model: "ensemble" }
History      → GET  /market/history/AAPL → OHLCV[]
```

### WebSocket (streaming):
```
Client connects → ws://host/ws?token=<jwt>
Client sends    → { type: "subscribe", channel: "signals", symbols: ["AAPL"] }
Server streams  → { type: "signal", channel: "signals", data: TradeSignal, timestamp: ... }
                → { type: "tick", channel: "ticks", data: TickData, timestamp: ... }
                → { type: "metrics", channel: "metrics", data: PortfolioMetrics, timestamp: ... }
                → { type: "log", channel: "logs", data: LogEntry, timestamp: ... }
                → { type: "agent_status", channel: "agent_status", data: AgentState, ... }
                → { type: "regime_change", channel: "regime_change", data: "bull", ... }
```

---

## B. Folder Structure

```
src/
├── App.tsx                    # Root: routing, QueryClient, auth init
├── main.tsx                   # Vite entry point
│
├── types/
│   └── index.ts               # All TypeScript interfaces and types
│                               # Single source of truth for shapes
│
├── services/
│   ├── api.ts                 # Axios instance, JWT interceptors, endpoints
│   └── websocket.ts           # WS class: connect/reconnect/subscribe/dispatch
│                               # Singleton pattern, lives outside React
│
├── store/
│   └── index.ts               # Zustand stores: auth, UI, profile, agents
│                               # Client-only state (no server data here)
│
├── hooks/
│   ├── index.ts               # Barrel export
│   ├── useTradeSocket.ts      # WS hook: batched updates, subscriptions, cleanup
│   └── useQueries.ts          # React Query hooks: usePortfolioMetrics, etc.
│                               # Each hook = one API concern
│
├── pages/
│   ├── LoginPage.tsx           # Auth form → POST /auth/login
│   ├── SignupPage.tsx          # Auth form → POST /auth/signup
│   ├── DashboardPage.tsx       # Main trading UI: metrics, chart, signals, logs
│   └── SettingsPage.tsx        # Profile editing, reward weights, risk params
│
├── layouts/
│   └── DashboardLayout.tsx     # Sidebar + main area + user menu
│
├── components/
│   ├── ui/                    # Reusable primitives (Button, Input, Badge, Card)
│   ├── charts/                # TradingChart (Lightweight Charts wrapper)
│   ├── auth/                  # AuthGuard, LoginForm, etc.
│   ├── dashboard/             # MetricCard, SignalFeed, PositionTable
│   ├── agents/                # AgentControls, ModelSelector, StatusIndicator
│   └── logs/                  # LogTerminal, LogLine, LogFilter
│
├── features/                  # Feature-sliced modules (for larger scale)
│   ├── trading/               # Trading-specific logic and components
│   └── analytics/             # Performance analysis views
│
└── utils/
    ├── formatters.ts          # fmtMoney, fmtPct, fmtDate, etc.
    └── constants.ts           # App-wide constants, default configs
```

### Responsibility summary:
| Directory    | Role | Changes when... |
|-------------|------|-----------------|
| `types/`     | Shape definitions | API contract changes |
| `services/`  | Network layer (no React) | Backend URL/auth changes |
| `store/`     | Client state | UI features added |
| `hooks/`     | React ↔ services bridge | New data sources |
| `pages/`     | Route-level views | New pages |
| `layouts/`   | Shell/chrome | Navigation changes |
| `components/`| Reusable UI pieces | Design system updates |

---

## C. Core Code Summary

### App.tsx
- QueryClientProvider wraps everything (TanStack Query)
- BrowserRouter with nested routes
- AuthGuard component: checks Zustand auth state, redirects to /login
- AuthInitializer: on mount, calls GET /auth/me to restore session

### DashboardPage.tsx
- Uses `useTradeSocket` hook for all real-time data
- Grid layout: metrics bar (6 cards) → chart + agent panel → log terminal
- Memoized MetricCard to avoid re-renders on unrelated updates
- Log terminal with severity filter (ALL/INFO/WARN/ERROR)
- Agent controls: start/stop, paper/live toggle, model selector

### useTradeSocket.ts
- Connects to WS on mount, disconnects on unmount
- Subscribes to channels: ticks, signals, metrics, logs, agent_status
- Batches updates every 250ms to prevent re-render storms
- Uses refs for pending updates to avoid stale closures
- Returns: { signals, metrics, ticks, logs, agentStatus, regime, isConnected }

---

## D. API Layer

### Interceptor flow:
```
Request  → attach Authorization: Bearer <token>
Response → 200: return data
         → 401: queue request → POST /auth/refresh → retry with new token
         → 401 on refresh: dispatch "auth:logout" event → redirect to login
```

### Endpoint map:
| Method | Path | Purpose |
|--------|------|---------|
| POST | /auth/login | Returns { accessToken, user } + sets refresh cookie |
| POST | /auth/signup | Same as login |
| POST | /auth/refresh | Uses HTTP-only cookie, returns new accessToken |
| POST | /auth/logout | Clears refresh cookie |
| GET | /auth/me | Returns current user from token |
| GET | /profile | Get trading profile |
| PATCH | /profile | Update profile (partial) |
| GET | /agents/status | All agents with status |
| POST | /agents/control | { action, model, mode } |
| GET | /portfolio/metrics | Current PortfolioMetrics |
| GET | /portfolio/positions | Open Position[] |
| GET | /market/history/:symbol | OHLCV[] for charting |

---

## E. State Design

### React Query (server state):
```
useQuery(["profile"])              → cached 5min, manual invalidation on save
useQuery(["agents", "status"])     → cached 10s, polls every 15s as WS backup
useQuery(["portfolio", "metrics"]) → cached 5s, polls every 10s
useQuery(["market", "history", symbol]) → cached 30s, per-symbol
```

### Zustand (client state):
```
useAuthStore     → { user, isAuthenticated, isLoading, setUser, logout }
useUIStore       → { theme, sidebarOpen, activeTab, chartSymbol, logFilter }
useProfileStore  → { activeProfile, setProfile, updateProfile }
useAgentStore    → { agents[], activeAgentId, updateAgent }
```

Why this split: React Query handles cache invalidation, refetching, and optimistic updates for server data. Zustand handles UI toggles, auth token (in memory), and preferences that don't need server sync.

---

## F. User Profile Schema

```typescript
interface TradingProfile {
  id: string;
  userId: string;
  riskTolerance: "low" | "medium" | "high";
  assetClasses: ("stocks" | "crypto" | "forex" | "commodities")[];
  selectedModel: "ppo" | "sac" | "ensemble" | "ppo_lstm" | "sac_lstm";
  capitalAllocation: number;      // e.g. 100000
  maxDrawdown: number;            // e.g. 0.15 = 15%
  stopLossPct: number;            // e.g. 0.05 = 5%
  takeProfitPct: number;          // e.g. 0.15 = 15%
  rewardWeights: {
    w1: number;  // Annualized return     (default 0.35)
    w2: number;  // Downside deviation    (default 0.25)
    w3: number;  // Differential return   (default 0.20)
    w4: number;  // Treynor ratio         (default 0.20)
  };
  createdAt: string;              // ISO 8601
  updatedAt: string;
}
```

---

## G. Production Considerations

### Scaling for multi-user, high-frequency data:
- **WS fan-out**: Use Redis pub/sub behind the FastAPI WS manager. Each server instance subscribes to Redis channels; user connections fan out locally. This lets you horizontally scale WS servers behind a load balancer.
- **Data batching**: The `useTradeSocket` hook already batches at 250ms. For HFT (>100 ticks/sec), increase to 500ms or use Web Workers to parse messages off the main thread.
- **Virtual scrolling**: For the log terminal and trade history, use `@tanstack/react-virtual` once lists exceed 500 items. The current implementation caps at 500 entries.
- **Chart performance**: Lightweight Charts handles 10K+ candles natively. For tick-level data, downsample server-side before sending.

### Security:
- Access token in memory only (Zustand, not localStorage) — immune to XSS
- Refresh token in HTTP-only, Secure, SameSite=Strict cookie — immune to JS access
- CORS: whitelist frontend origin only
- Rate limiting on /auth endpoints (e.g., 5 attempts/minute)
- Input validation: Zod on frontend, Pydantic on backend
- WS authentication: token passed as query param on connect, validated server-side

### Performance optimization:
- `React.memo` on MetricCard and LogLine — these render 6x and 500x respectively
- Batched state updates in useTradeSocket (avoids 100+ re-renders/sec)
- React Query `staleTime` tuned per data type (5s for fast data, 5min for profiles)
- Code splitting: lazy-load pages with `React.lazy` + `Suspense`
- Tailwind CSS purge removes unused classes in production build

### Docker setup:
```yaml
# docker-compose.yml
services:
  frontend:
    build: ./rl-dashboard
    ports: ["3000:80"]
    depends_on: [backend]

  backend:
    build: ./rl-trading-system
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/trading
      - REDIS_URL=redis://redis:6379
    depends_on: [db, redis]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: trading
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

### Running it:
```bash
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```
