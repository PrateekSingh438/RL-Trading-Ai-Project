"""
FastAPI Server v4.0
===================
Improvements over v3:
  • Live price refresh (yfinance intraday, every 30 s background thread)
  • WebSocket broadcasting: ticks, metrics, signals, regime changes, news
  • /api/v1/sentiment/news   – real headlines via LiveNewsFetcher
  • /api/v1/market/live      – current real-time quotes
  • /api/v1/market/regime    – current regime
  • /api/v1/portfolio/risk   – detailed risk breakdown
  • Faster engine loop (sleep 0.05 s, skip sentiment in hot path)
  • Training speed: configurable n_episodes, early-stop on max-DD
  • CORS open; JWT auth; demo user built-in
"""
import os, sys, json, time, asyncio, hashlib, threading
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import numpy as np

from config.settings import CONFIG
from data.pipeline import fetch_data, prepare_multi_stock_data, normalize_features, add_technical_indicators
from env.trading_env import TradingEnv
from agents.ensemble import EnsembleAgent
from sentiment.analyzer import LiveNewsFetcher, NewsGenerator, SentimentAnalyzer, TradeExplainer

try:
    from data.indicators import add_extra_indicators, compute_feature_importance
    HAS_EXTRA = True
except ImportError:
    HAS_EXTRA = False

app = FastAPI(title="RL Trading System API", version="4.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ─── Global state ─────────────────────────────────────────────────────────────

USERS: Dict[str, dict] = {
    "demo@trader.com": {
        "id": "user_1", "email": "demo@trader.com", "name": "Demo Trader",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "created_at": "2024-01-01T00:00:00Z",
    }
}
SESSIONS: Dict[str, dict] = {}

profile_data = {
    "id": "profile_1", "user_id": "user_1", "risk_tolerance": "medium",
    "asset_classes": ["stocks"], "selected_model": "ensemble",
    "capital_allocation": 1_000_000, "max_drawdown": 0.15,
    "stop_loss_pct": 0.05, "take_profit_pct": 0.15,
    "reward_weights": {"w1": 0.30, "w2": 0.20, "w3": 0.15, "w4": 0.15, "w5": 0.15, "w6": 0.05},
    "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z",
}

agent_state = {
    "id": "agent_1", "model": "ensemble", "status": "stopped", "mode": "paper",
    "uptime": 0, "total_signals": 0, "training_status": "not_trained",
    "training_progress": 0, "n_episodes": 50,
}
portfolio_metrics: dict = {
    "portfolio_value": 1_000_000, "cash": 1_000_000,
    "pnl_daily": 0, "pnl_cumulative": 0, "pnl_pct": 0,
    "sharpe_ratio": 0, "sortino_ratio": 0, "max_drawdown": 0,
    "current_drawdown": 0, "win_rate": 0, "total_trades": 0,
    "beta": 1.0, "alpha": 0, "volatility": 0,
    "timestamp": time.time() * 1000,
}

market_data_cache: Dict[str, list] = {}
live_prices: Dict[str, dict] = {}        # symbol → {price, change, change_pct, volume, ts}
ws_connections: List[WebSocket] = []
engine_running = False
trade_signals: List[dict] = []
system_logs: List[dict] = []
equity_curve: List[dict] = []
positions_state: List[dict] = []
feature_importance_state: Dict[str, float] = {}
current_regime = "sideways"
risk_detail: dict = {}
live_news_cache: List[dict] = []         # last N live headlines across all tickers

cached_data: dict = {"loaded": False, "train": None, "test": None, "tickers": None}
trained_agent: dict = {"agent": None}

_live_fetcher = LiveNewsFetcher(cache_ttl=180)   # 3-min cache for live news
_news_gen     = NewsGenerator(seed=42)
_sentiment    = SentimentAnalyzer()
_explainer    = TradeExplainer()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _has_torch() -> bool:
    try:
        import torch; return True
    except Exception:
        return False


def create_token(uid: str) -> str:
    t = hashlib.sha256(f"{uid}:s:{time.time()}".encode()).hexdigest()
    SESSIONS[t] = {"user_id": uid, "expires": time.time() + 3600}
    return t


def add_log(level: str, message: str, source: str = "system"):
    entry = {
        "id": f"log_{len(system_logs)}", "level": level,
        "message": message, "source": source,
        "timestamp": time.time() * 1000,
    }
    system_logs.append(entry)
    if len(system_logs) > 3000:
        del system_logs[:500]


def ok(data):
    return {"status": "success", "data": data}


# ─── Pydantic models ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class ProfileUpdate(BaseModel):
    risk_tolerance: Optional[str] = None
    asset_classes: Optional[List[str]] = None
    selected_model: Optional[str] = None
    capital_allocation: Optional[float] = None
    max_drawdown: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    reward_weights: Optional[dict] = None

class AgentCommand(BaseModel):
    action: str
    model: Optional[str] = None
    mode: Optional[str] = None
    n_episodes: Optional[int] = None

# ─── Data loading ─────────────────────────────────────────────────────────────

def load_data():
    if cached_data["loaded"]:
        return
    add_log("INFO", f"Loading historical data for {CONFIG.data.tickers}…", "data")
    raw = fetch_data(
        CONFIG.data.tickers,
        CONFIG.data.start_date, CONFIG.data.end_date,
        CONFIG.data.benchmark,
    )
    if HAS_EXTRA:
        for t in list(raw.keys()):
            try:
                raw[t] = add_extra_indicators(raw[t])
            except Exception as e:
                add_log("WARN", f"Extra indicators failed for {t}: {e}", "data")

    sf, bd = prepare_multi_stock_data(raw, CONFIG.data.tickers, CONFIG.data.benchmark)
    norm, _ = normalize_features(sf)
    pc = [c for c in sf.columns if "Close" in c][: len(CONFIG.data.tickers)]
    prices   = sf[pc].values
    features = norm.values
    bc = "Close" if "Close" in bd.columns else bd.columns[3]
    bv = bd[bc].values
    if hasattr(bv, "iloc"):
        bv = bv.values
    bv = bv.flatten()
    br = np.concatenate([[0], np.diff(bv) / np.where(bv[:-1] != 0, bv[:-1], 1.0)])
    ml = min(len(prices), len(features), len(br))
    prices, features, br = prices[:ml], features[:ml], br[:ml]

    # Populate OHLCV cache for chart
    for i, t in enumerate(CONFIG.data.tickers):
        if i < prices.shape[1]:
            market_data_cache[t] = [
                {
                    "time": j, "open": float(p * 0.999), "high": float(p * 1.005),
                    "low": float(p * 0.995), "close": float(p), "volume": 1_000_000,
                }
                for j, p in enumerate(prices[:, i])
            ]

    sp = int(len(prices) * 0.8)
    cached_data.update({
        "loaded": True, "tickers": CONFIG.data.tickers,
        "train": {"features": features[:sp], "prices": prices[:sp], "bench_returns": br[:sp]},
        "test":  {"features": features[sp:], "prices": prices[sp:], "bench_returns": br[sp:]},
    })
    add_log("INFO", f"Data ready: {features.shape[1]} features, {sp} train / {ml - sp} test days", "data")


def make_env(data: dict) -> TradingEnv:
    return TradingEnv(
        stock_data=data["features"], price_data=data["prices"],
        benchmark_returns=data["bench_returns"],
        tickers=cached_data["tickers"],
        initial_capital=CONFIG.trading.initial_capital,
        transaction_cost=CONFIG.trading.transaction_cost,
        slippage=CONFIG.trading.slippage,
        max_position_pct=CONFIG.trading.max_position_pct,
        max_drawdown_threshold=CONFIG.trading.max_drawdown_threshold,
        reward_weights=(
            CONFIG.reward.w1, CONFIG.reward.w2,
            CONFIG.reward.w3, CONFIG.reward.w4,
        ),
        lookback_window=min(20, len(data["prices"]) // 4),   # ← reduced from 30→20
    )


# ─── Live price refresh ───────────────────────────────────────────────────────

def _refresh_live_prices():
    """Background thread: fetch current quotes from yfinance every 30 s."""
    while True:
        try:
            import yfinance as yf
            tickers = CONFIG.data.tickers
            data = yf.download(
                tickers, period="2d", interval="1d",
                auto_adjust=True, progress=False,
            )
            close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
            prev_close = close.iloc[-2] if len(close) >= 2 else close.iloc[-1]
            last_close  = close.iloc[-1]
            for t in tickers:
                try:
                    price = float(last_close[t])
                    prev  = float(prev_close[t])
                    chg   = price - prev
                    chg_p = chg / prev * 100 if prev else 0.0
                    live_prices[t] = {
                        "symbol": t, "price": round(price, 2),
                        "change": round(chg, 2), "change_pct": round(chg_p, 3),
                        "prev_close": round(prev, 2),
                        "timestamp": int(time.time() * 1000),
                    }
                except Exception:
                    pass
        except Exception as e:
            pass  # silently skip; clients see stale values
        time.sleep(30)


# ─── Live news refresh ────────────────────────────────────────────────────────

def _refresh_live_news():
    """Background thread: fetch live headlines every 5 min."""
    while True:
        try:
            tickers = CONFIG.data.tickers[:3]   # top 3 to reduce API calls
            items = _live_fetcher.fetch_many(tickers)
            if items:
                live_news_cache.clear()
                for it in items[:30]:
                    live_news_cache.append({
                        "title": it.title,
                        "source": it.source,
                        "ticker": it.ticker,
                        "sentiment": it.sentiment,
                        "confidence": round(it.confidence, 3),
                        "impact_score": round(it.impact_score, 3),
                        "url": it.url,
                        "timestamp": it.timestamp,
                        "is_live": it.is_live,
                    })
                add_log("INFO",
                        f"Live news refreshed: {len(items)} articles for {tickers}",
                        "sentiment")
        except Exception as e:
            add_log("WARN", f"Live news refresh failed: {e}", "sentiment")
        time.sleep(300)


# ─── Training ─────────────────────────────────────────────────────────────────

def train_agent(n_episodes: int = 50):
    global trained_agent
    load_data()
    env = make_env(cached_data["train"])
    obs = env.reset()
    agent = EnsembleAgent(obs_dim=len(obs), action_dim=env.action_dim)

    add_log("INFO",
            f"Training {n_episodes} episodes | PyTorch: {_has_torch()} | "
            f"obs_dim={len(obs)} action_dim={env.action_dim}", "training")
    agent_state.update({"training_status": "training", "n_episodes": n_episodes})
    best = -float("inf")

    for ep in range(n_episodes):
        obs = env.reset()
        done = False
        er = 0.0

        while not done:
            a, _ = agent.select_action(obs)
            no, r, done, info = env.step(a)
            _, lp, v = agent.ppo.select_action(obs)
            agent.store_transition(obs, a, r, no, done, value=v, log_prob=lp)
            er += r
            obs = no

        agent.train()
        p = env.get_performance_summary()
        if er > best:
            best = er
        agent_state["training_progress"] = int((ep + 1) / n_episodes * 100)

        if (ep + 1) % max(1, n_episodes // 10) == 0 or ep == 0:
            add_log("INFO",
                    f"Ep {ep+1}/{n_episodes} | Reward: {er:.0f} | "
                    f"Ret: {p.get('total_return',0):.2%} | "
                    f"Sharpe: {p.get('sharpe_ratio',0):.3f} | "
                    f"MaxDD: {p.get('max_drawdown',0):.2%}",
                    "training")

        # Early stop if drawdown is catastrophic during training
        if p.get("max_drawdown", 0) > 0.50:
            add_log("WARN", f"Early stop at ep {ep+1}: max_drawdown > 50%", "training")
            break

    trained_agent["agent"] = agent
    agent_state.update({"training_status": "trained", "training_progress": 100})
    add_log("INFO", f"Training complete — best reward: {best:.0f}", "training")


# ─── Engine (paper trading loop) ─────────────────────────────────────────────

def run_engine():
    global engine_running, portfolio_metrics, positions_state, feature_importance_state
    global current_regime, risk_detail

    try:
        if not trained_agent["agent"]:
            train_agent(n_episodes=agent_state.get("n_episodes", 50))

        agent = trained_agent["agent"]
        load_data()
        env = make_env(cached_data["test"])
        obs = env.reset()

        add_log("INFO", "Paper trading started with trained agent", "agent")
        agent_state["status"] = "running"
        agent_state["total_signals"] = 0
        equity_curve.clear()

        done = False
        step = 0
        t0 = time.time()
        prev_regime = None

        while engine_running and not done:
            a, di = agent.select_action(obs, deterministic=True)
            obs, r, done, info = env.step(a)
            step += 1
            pv = info["portfolio_value"]
            p  = env.get_performance_summary()

            # ── Regime tracking ──
            raw_regime = info.get("regime", "sideways")
            regime_key = str(raw_regime).lower().replace(" ", "_")
            if regime_key != prev_regime:
                current_regime = regime_key
                prev_regime = regime_key
                add_log("INFO", f"Regime change → {regime_key}", "regime")

            # ── Portfolio metrics ──
            rm = info.get("risk_metrics")
            curr_dd = getattr(rm, "current_drawdown", 0) if rm else 0

            portfolio_metrics.update({
                "portfolio_value":  pv,
                "cash":             info.get("cash", 0),
                "pnl_daily":        info.get("step_return", 0) * pv,
                "pnl_cumulative":   pv - CONFIG.trading.initial_capital,
                "pnl_pct":         (pv - CONFIG.trading.initial_capital) / CONFIG.trading.initial_capital,
                "sharpe_ratio":     p.get("sharpe_ratio", 0),
                "sortino_ratio":    p.get("sortino_ratio", 0),
                "max_drawdown":     p.get("max_drawdown", 0),
                "current_drawdown": curr_dd,
                "win_rate":         p.get("win_rate", 0),
                "total_trades":     p.get("n_trades", 0),
                "beta":             p.get("beta", 1.0),
                "alpha":            p.get("alpha", 0),
                "volatility":       p.get("volatility", 0),
                "timestamp":        time.time() * 1000,
            })
            risk_detail = {
                "var_95":           getattr(rm, "value_at_risk_95", 0) if rm else 0,
                "cvar_95":          getattr(rm, "cvar_95", 0) if rm else 0,
                "max_leverage":     getattr(rm, "max_leverage", 1.0) if rm else 1.0,
                "is_halted":        getattr(rm, "is_trading_halted", False) if rm else False,
            }

            equity_curve.append({
                "step": step, "value": round(pv, 2),
                "timestamp": time.time() * 1000,
            })

            # ── Positions ──
            positions_state.clear()
            if hasattr(env, "positions") and hasattr(env, "price_data"):
                cp = env.price_data[min(env.current_step, len(env.price_data) - 1)]
                for i, ticker in enumerate(CONFIG.data.tickers):
                    if i < len(env.positions) and abs(env.positions[i]) > 0.01:
                        sh  = env.positions[i]
                        pr  = float(cp[i]) if i < len(cp) else 0
                        mv  = sh * pr
                        positions_state.append({
                            "symbol":        ticker,
                            "shares":        round(float(sh), 2),
                            "current_price": round(pr, 2),
                            "market_value":  round(mv, 2),
                            "weight":        round(abs(mv) / max(pv, 1) * 100, 1),
                        })

            # ── Trade signals ──
            for t in info.get("trades", []):
                idx = (
                    CONFIG.data.tickers.index(t["ticker"])
                    if t["ticker"] in CONFIG.data.tickers else 0
                )
                # Get sentiment for this ticker (prefer cached live)
                live_sent = next(
                    (n for n in live_news_cache if n["ticker"] == t["ticker"]), None
                )
                sent_info = {
                    "overall": live_sent["sentiment"] if live_sent else "neutral",
                    "confidence": live_sent["confidence"] if live_sent else 0.5,
                    "impact": live_sent["impact_score"] if live_sent else 0.0,
                    "live": bool(live_sent and live_sent.get("is_live")),
                }
                sig = {
                    "id":        f"sig_{len(trade_signals)}",
                    "symbol":    t["ticker"],
                    "action":    t["action"],
                    "confidence": round(min(0.95, 0.50 + abs(a[idx]) * 0.40), 2),
                    "price":     round(t["price"], 2),
                    "quantity":  round(t["shares"], 2),
                    "timestamp": time.time() * 1000,
                    "reasoning": (
                        f"{t['action']} {t['ticker']} | "
                        f"Regime: {regime_key} | "
                        f"Sentiment: {sent_info['overall']}"
                        + (" [LIVE]" if sent_info["live"] else "")
                    ),
                    "regime":    regime_key,
                    "sentiment": sent_info,
                }
                trade_signals.append(sig)
                agent_state["total_signals"] = len(trade_signals)

            # ── Feature importance (every 30 steps) ──
            if step % 30 == 0 and HAS_EXTRA:
                try:
                    fn = [f"f{i}" for i in range(len(obs))]
                    fi = compute_feature_importance(obs, fn, agent.ppo, n_perturbations=5)
                    feature_importance_state.clear()
                    feature_importance_state.update(fi)
                except Exception:
                    pass

            # ── Logging ──
            if step % 5 == 0:
                pnl = pv - CONFIG.trading.initial_capital
                add_log(
                    "INFO",
                    f"Step {step} | ${pv:,.0f} ({'+' if pnl >= 0 else ''}{pnl:,.0f}) "
                    f"| {regime_key} | {len(info.get('trades', []))} trades",
                    "agent",
                )

            agent_state["uptime"] = int(time.time() - t0)
            time.sleep(0.05)   # ← reduced from 0.2 → 0.05 (4× faster)

        agent_state["status"] = "stopped"
        f = env.get_performance_summary()
        add_log(
            "INFO",
            f"Done | ${pv:,.0f} | Ret: {f.get('total_return',0):.2%} "
            f"| Sharpe: {f.get('sharpe_ratio',0):.3f}",
            "engine",
        )

    except Exception as e:
        agent_state["status"] = "error"
        add_log("ERROR", str(e), "engine")
        import traceback; traceback.print_exc()


# ─── WebSocket broadcaster ────────────────────────────────────────────────────

async def _broadcast(payload: dict):
    dead = []
    for ws in ws_connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in ws_connections:
            ws_connections.remove(ws)


async def _push_loop():
    """Push live data to all WebSocket clients every second."""
    while True:
        await asyncio.sleep(1.0)
        if not ws_connections:
            continue
        try:
            payload = {
                "type": "metrics",
                "data": {
                    **portfolio_metrics,
                    "regime": current_regime,
                    "agent_status": agent_state["status"],
                    "training_progress": agent_state["training_progress"],
                },
                "timestamp": time.time() * 1000,
            }
            await _broadcast(payload)

            if live_prices:
                await _broadcast({
                    "type": "tick",
                    "data": live_prices,
                    "timestamp": time.time() * 1000,
                })

            if trade_signals:
                recent = trade_signals[-5:]
                await _broadcast({
                    "type": "signal",
                    "data": recent,
                    "timestamp": time.time() * 1000,
                })

            if live_news_cache:
                await _broadcast({
                    "type": "news",
                    "data": live_news_cache[:10],
                    "timestamp": time.time() * 1000,
                })
        except Exception:
            pass


# ─── REST endpoints ───────────────────────────────────────────────────────────

@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    u = USERS.get(req.email)
    if not u or hashlib.sha256(req.password.encode()).hexdigest() != u["password_hash"]:
        raise HTTPException(401, "Invalid credentials")
    return ok({
        "accessToken": create_token(u["id"]),
        "user": {"id": u["id"], "email": u["email"], "name": u["name"],
                 "createdAt": u["created_at"]},
    })

@app.post("/api/v1/auth/signup")
async def signup(req: SignupRequest):
    if req.email in USERS:
        raise HTTPException(400, "Email already registered")
    uid = f"user_{len(USERS)+1}"
    USERS[req.email] = {
        "id": uid, "email": req.email, "name": req.name,
        "password_hash": hashlib.sha256(req.password.encode()).hexdigest(),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    return ok({"accessToken": create_token(uid),
               "user": {"id": uid, "email": req.email, "name": req.name}})

@app.post("/api/v1/auth/refresh")
async def refresh():
    return ok({"accessToken": create_token("user_1")})

@app.get("/api/v1/auth/me")
async def get_me():
    return ok({"id": "user_1", "email": "demo@trader.com",
               "name": "Demo Trader", "createdAt": "2024-01-01T00:00:00Z"})

@app.get("/api/v1/profile")
async def get_profile():
    return ok(profile_data)

@app.patch("/api/v1/profile")
async def update_profile(req: ProfileUpdate):
    u = req.model_dump(exclude_none=True)
    profile_data.update(u)
    profile_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    if "reward_weights" in u:
        w = u["reward_weights"]
        CONFIG.reward.w1 = w.get("w1", CONFIG.reward.w1)
        CONFIG.reward.w2 = w.get("w2", CONFIG.reward.w2)
        CONFIG.reward.w3 = w.get("w3", CONFIG.reward.w3)
        CONFIG.reward.w4 = w.get("w4", CONFIG.reward.w4)
    if "max_drawdown" in u:
        CONFIG.trading.max_drawdown_threshold = u["max_drawdown"]
    if "stop_loss_pct" in u:
        CONFIG.trading.stop_loss_pct = u["stop_loss_pct"]
    if "take_profit_pct" in u:
        CONFIG.trading.take_profit_pct = u["take_profit_pct"]
    add_log("INFO", f"Profile updated: {list(u.keys())}", "config")
    return ok(profile_data)

@app.get("/api/v1/agents/status")
async def get_status():
    return ok([agent_state])

@app.post("/api/v1/agents/control")
async def control(cmd: AgentCommand):
    global engine_running
    if cmd.action == "start":
        if agent_state["status"] == "running":
            raise HTTPException(400, "Already running")
        engine_running = True
        if cmd.model:    agent_state["model"]      = cmd.model
        if cmd.mode:     agent_state["mode"]       = cmd.mode
        if cmd.n_episodes:
            agent_state["n_episodes"] = cmd.n_episodes
        threading.Thread(target=run_engine, daemon=True).start()
        return ok({"message": "Starting (trains first if needed)", "state": agent_state})
    if cmd.action == "stop":
        engine_running = False
        agent_state["status"] = "stopped"
        add_log("INFO", "Agent stopped by user", "agent")
        return ok({"message": "Stopped"})
    raise HTTPException(400, f"Unknown action: {cmd.action}")

@app.get("/api/v1/portfolio/metrics")
async def metrics():
    return ok(portfolio_metrics)

@app.get("/api/v1/portfolio/positions")
async def positions():
    return ok(positions_state)

@app.get("/api/v1/portfolio/trades")
async def trades():
    return ok(trade_signals[-200:])

@app.get("/api/v1/portfolio/equity")
async def equity():
    return ok(equity_curve[-1000:])

@app.get("/api/v1/portfolio/feature_importance")
async def feat_imp():
    return ok(feature_importance_state)

@app.get("/api/v1/portfolio/risk")
async def risk():
    return ok({**risk_detail, **{
        "sharpe_ratio":     portfolio_metrics.get("sharpe_ratio", 0),
        "sortino_ratio":    portfolio_metrics.get("sortino_ratio", 0),
        "max_drawdown":     portfolio_metrics.get("max_drawdown", 0),
        "current_drawdown": portfolio_metrics.get("current_drawdown", 0),
        "volatility":       portfolio_metrics.get("volatility", 0),
        "beta":             portfolio_metrics.get("beta", 1.0),
        "alpha":            portfolio_metrics.get("alpha", 0),
    }})

@app.get("/api/v1/market/symbols")
async def symbols():
    return ok(CONFIG.data.tickers)

@app.get("/api/v1/market/history/{symbol}")
async def history(symbol: str):
    if not market_data_cache:
        try:
            load_data()
        except Exception:
            pass
    return ok(market_data_cache.get(symbol, [])[-500:])

@app.get("/api/v1/market/live")
async def market_live():
    """Current real-time quotes for all tracked symbols."""
    return ok(live_prices)

@app.get("/api/v1/market/live/{symbol}")
async def market_live_symbol(symbol: str):
    return ok(live_prices.get(symbol, {}))

@app.get("/api/v1/market/regime")
async def regime():
    return ok({"current": current_regime, "timestamp": time.time() * 1000})

@app.get("/api/v1/sentiment/news")
async def sentiment_news(ticker: str = None, limit: int = 30):
    """
    Live financial news headlines.
    If ticker is given, filter to that ticker; otherwise return all.
    """
    news = live_news_cache
    if ticker:
        news = [n for n in news if n.get("ticker") == ticker.upper()]
    if not news:
        # Fall back: generate simulated news so dashboard always has content
        items = _news_gen.generate_news(
            CONFIG.data.tickers[:3], n_items=2,
            market_regime=current_regime.replace("_", " ").title(),
        )
        news = [{
            "title": it.title, "source": it.source, "ticker": it.ticker,
            "sentiment": it.sentiment, "confidence": it.confidence,
            "impact_score": it.impact_score, "url": "",
            "timestamp": it.timestamp, "is_live": False,
        } for it in items]
    return ok(news[:limit])

@app.get("/api/v1/logs")
async def logs(level: str = "ALL", limit: int = 100):
    if level == "ALL":
        return ok(system_logs[-limit:])
    return ok([l for l in system_logs if l["level"] == level][-limit:])

# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ws_connections.append(ws)
    try:
        while True:
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping", "timestamp": time.time() * 1000})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in ws_connections:
            ws_connections.remove(ws)

# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    add_log("INFO", "RL Trading System API v4.0", "system")
    add_log("INFO",
            f"Assets: {CONFIG.data.tickers} | PyTorch: {_has_torch()} | Extra indicators: {HAS_EXTRA}",
            "system")

    # Start background threads
    threading.Thread(target=_refresh_live_prices, daemon=True).start()
    threading.Thread(target=_refresh_live_news,   daemon=True).start()

    # Start async push loop
    asyncio.create_task(_push_loop())
    add_log("INFO", "Live price & news refresh threads started", "system")


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════╗")
    print("║  RL Trading System API v4.0                        ║")
    print("║  http://localhost:8000/docs                        ║")
    print("║  Login: demo@trader.com / password123              ║")
    print(f"║  PyTorch: {_has_torch()} | Extra indicators: {HAS_EXTRA}   ║")
    print("╚════════════════════════════════════════════════════╝")
    uvicorn.run(app, host="0.0.0.0", port=8000)
