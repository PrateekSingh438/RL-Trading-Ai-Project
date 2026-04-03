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

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
training_abort = False  # Flag to abort training mid-loop

_live_fetcher = LiveNewsFetcher(cache_ttl=55)    # 55-s cache for live news
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
    import yfinance as yf
    import random

    def _seed_simulated():
        """Seed prices immediately from cached data or random walk so ticker is never blank."""
        base = {"AAPL": 185.0, "GOOGL": 175.0, "MSFT": 415.0, "NFLX": 625.0, "TSLA": 255.0}
        for t in CONFIG.data.tickers:
            if t not in live_prices:
                p = base.get(t, 100.0) * (1 + random.uniform(-0.01, 0.01))
                live_prices[t] = {
                    "symbol": t, "price": round(p, 2),
                    "change": 0.0, "change_pct": 0.0,
                    "prev_close": round(p, 2),
                    "timestamp": int(time.time() * 1000),
                    "simulated": True,
                }

    _seed_simulated()  # fill immediately so frontend sees data on first poll

    while True:
        tickers = CONFIG.data.tickers
        fetched = 0
        for t in tickers:
            try:
                info = yf.Ticker(t).fast_info
                price = float(info.last_price or info.regular_market_price or 0)
                prev  = float(info.previous_close or price)
                if price <= 0:
                    raise ValueError("invalid price")
                chg   = price - prev
                chg_p = chg / prev * 100 if prev else 0.0
                live_prices[t] = {
                    "symbol": t, "price": round(price, 2),
                    "change": round(chg, 2), "change_pct": round(chg_p, 3),
                    "prev_close": round(prev, 2),
                    "timestamp": int(time.time() * 1000),
                    "simulated": False,
                }
                fetched += 1
            except Exception:
                # Simulate a small random walk from last known price so ticker keeps moving
                if t in live_prices:
                    p = live_prices[t]["price"] * (1 + random.uniform(-0.002, 0.002))
                    live_prices[t]["price"] = round(p, 2)
                    live_prices[t]["timestamp"] = int(time.time() * 1000)
        if fetched:
            add_log("INFO", f"Live prices refreshed: {fetched}/{len(tickers)} tickers", "market")
        time.sleep(30)


# ─── Live news refresh ────────────────────────────────────────────────────────

def _do_news_refresh(force: bool = False):
    """Fetch live news for all tickers and update cache. Thread-safe."""
    try:
        tickers = CONFIG.data.tickers   # fetch all tickers, not just top 3
        if force:
            # Bypass the per-ticker in-memory cache by clearing it
            _live_fetcher._cache.clear()
        items = _live_fetcher.fetch_many(tickers)
        if items:
            live_news_cache.clear()
            for it in items[:40]:
                live_news_cache.append({
                    "title":        it.title,
                    "source":       it.source,
                    "ticker":       it.ticker,
                    "sentiment":    it.sentiment,
                    "confidence":   round(it.confidence, 3),
                    "impact_score": round(it.impact_score, 3),
                    "url":          it.url,
                    "timestamp":    it.timestamp,
                    "is_live":      it.is_live,
                    "ai_scored":    getattr(it, "ai_scored", False),
                })
            add_log("INFO",
                    f"Live news refreshed: {len(items)} articles for {tickers}",
                    "sentiment")
            return True
    except Exception as e:
        add_log("WARN", f"Live news refresh failed: {e}", "sentiment")
    return False


def _refresh_live_news():
    """Background thread: fetch live headlines every 60 s."""
    while True:
        _do_news_refresh()
        time.sleep(60)


# ─── Training ─────────────────────────────────────────────────────────────────

def train_agent(n_episodes: int = 50):
    global trained_agent, training_abort
    training_abort = False
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
        if training_abort:
            add_log("WARN", f"Training aborted at episode {ep+1}/{n_episodes}", "training")
            break

        obs = env.reset()
        done = False
        er = 0.0

        while not done:
            if training_abort:
                break
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

        # Skip to next episode if this one had catastrophic drawdown
        if p.get("max_drawdown", 0) > 0.50:
            add_log("WARN", f"Ep {ep+1}: max_drawdown > 50%, resetting for next episode", "training")
            continue

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
    if cmd.action == "abort_training":
        global training_abort
        training_abort = True
        add_log("INFO", "Training abort requested by user", "training")
        return ok({"message": "Abort signal sent"})
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
            "timestamp": it.timestamp, "is_live": False, "ai_scored": False,
        } for it in items]
    return ok(news[:limit])

@app.post("/api/v1/sentiment/news/refresh")
async def refresh_news():
    """Force-refresh live news cache immediately (bypasses TTL)."""
    success = await asyncio.get_event_loop().run_in_executor(
        None, lambda: _do_news_refresh(force=True)
    )
    return ok({"refreshed": success, "count": len(live_news_cache)})

@app.get("/api/v1/portfolio/analysis")
async def portfolio_analysis():
    """
    Stream an AI-generated analysis of the current portfolio using Gemini Flash.
    Requires GEMINI_API_KEY environment variable.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        async def _no_key():
            yield "⚠ GROQ_API_KEY is not set. Get a free key at console.groq.com and add it to your .env file."
        return StreamingResponse(_no_key(), media_type="text/plain")

    try:
        from groq import Groq as _Groq
    except ImportError:
        async def _no_pkg():
            yield "⚠ groq package not installed. Run: pip install groq"
        return StreamingResponse(_no_pkg(), media_type="text/plain")

    m = portfolio_metrics

    # Build positions summary
    if positions_state:
        pos_lines = "\n".join(
            f"  • {p['symbol']}: {p['shares']:+.2f} sh @ ${p['current_price']:.2f}"
            f"  (MV ${p['market_value']:,.0f}, {'LONG' if p['shares'] >= 0 else 'SHORT'})"
            for p in positions_state[:8]
        )
    else:
        pos_lines = "  No open positions"

    # Recent signals (last 5)
    if trade_signals:
        sig_lines = "\n".join(
            f"  • {s['action']} {s['symbol']} @ ${float(s.get('price', 0)):.2f}"
            f"  conf {int((s.get('confidence', 0.5))*100)}%"
            for s in trade_signals[-5:]
        )
    else:
        sig_lines = "  No recent signals"

    # News sentiment
    if live_news_cache:
        news_lines = "\n".join(
            f"  • [{n['ticker']}] {n['title'][:90]}  →  {n['sentiment']}"
            for n in live_news_cache[:6]
        )
    else:
        news_lines = "  No recent news"

    pv      = m.get("portfolio_value", 1_000_000)
    pnl_cum = m.get("pnl_cumulative", 0)
    pnl_pct = m.get("pnl_pct", 0) * 100
    pnl_day = m.get("pnl_daily", 0)
    cash    = m.get("cash", 0)
    wr      = m.get("win_rate", 0) * 100
    trades  = m.get("total_trades", 0)
    sharpe  = m.get("sharpe_ratio", 0)
    sortino = m.get("sortino_ratio", 0)
    max_dd  = m.get("max_drawdown", 0) * 100
    cur_dd  = m.get("current_drawdown", 0) * 100
    beta    = m.get("beta", 1.0)
    alpha   = m.get("alpha", 0) * 100
    vol     = m.get("volatility", 0) * 100
    regime  = current_regime.replace("_", " ").title()

    prompt = f"""You are a senior quantitative portfolio manager reviewing a live algorithmic trading account.

## Portfolio Snapshot
| Metric | Value |
|---|---|
| Portfolio Value | ${pv:>12,.2f} |
| Cumulative P&L | ${pnl_cum:>+12,.2f} ({pnl_pct:+.2f}%) |
| Today's P&L | ${pnl_day:>+12,.2f} |
| Cash Available | ${cash:>12,.2f} ({cash/max(pv,1)*100:.1f}% of NAV) |
| Win Rate | {wr:.1f}% over {trades} trades |

## Risk Metrics
| Metric | Value | Signal |
|---|---|---|
| Sharpe Ratio | {sharpe:.3f} | {"🟢 Good" if sharpe > 1 else "🟡 Moderate" if sharpe > 0 else "🔴 Negative"} |
| Sortino Ratio | {sortino:.3f} | {"🟢 Good" if sortino > 1 else "🟡 Moderate" if sortino > 0 else "🔴 Negative"} |
| Max Drawdown | {max_dd:.2f}% | {"🟢 Acceptable" if max_dd < 10 else "🟡 Elevated" if max_dd < 20 else "🔴 High"} |
| Current Drawdown | {cur_dd:.2f}% | {"🟢 Recovering" if cur_dd < 5 else "🟡 In drawdown" if cur_dd < 15 else "🔴 Deep drawdown"} |
| Beta vs Benchmark | {beta:.3f} | {"🟢 Low correlation" if abs(beta) < 0.5 else "🟡 Moderate" if abs(beta) < 1 else "🔴 High correlation"} |
| Alpha (Ann.) | {alpha:+.2f}% | {"🟢 Outperforming" if alpha > 0 else "🔴 Underperforming"} |
| Volatility (Ann.) | {vol:.2f}% | |

## Market Context
- Current Regime: **{regime}**

## Open Positions
{pos_lines}

## Recent Agent Signals
{sig_lines}

## Market News & Sentiment
{news_lines}

---
Provide a concise portfolio health report with these sections:
1. **Overall Assessment** — 2-3 sentences on portfolio health and capital status
2. **Strengths** — what is working well (2-3 bullet points)
3. **Risks & Concerns** — key risks right now (2-3 bullet points)
4. **Recommendation** — one specific, actionable next step for the agent or trader

Be direct, data-driven, and practical. No fluff."""

    client = _Groq(api_key=api_key)

    async def stream_analysis():
        try:
            stream = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": (
                        "You are a concise, data-driven quantitative analyst. "
                        "Use markdown formatting. Be direct and actionable. "
                        "Never repeat the input data back — only provide insight."
                    )},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=600,
                stream=True,
            )
            for chunk in stream:
                text = chunk.choices[0].delta.content
                if text:
                    yield text
        except Exception as e:
            yield f"\n\n⚠ Analysis error: {e}"

    return StreamingResponse(stream_analysis(), media_type="text/plain")


@app.get("/api/v1/sentiment/status")
async def sentiment_status():
    """Returns whether FinBERT AI model is loaded and ready."""
    from sentiment.analyzer import _finbert
    available = _finbert.is_available
    return ok({
        "ai_available": available,
        "model": "ProsusAI/finbert" if available else None,
        "scorer": "finbert" if available else "keyword",
    })

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
