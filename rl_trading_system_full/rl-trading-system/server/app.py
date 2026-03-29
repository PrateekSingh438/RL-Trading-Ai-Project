"""
FastAPI Server v3.0
===================
- PyTorch PPO (if available)
- 50 training episodes
- Extra indicators (ATR, OBV, Ichimoku)
- Feature importance per trade
- Equity curve endpoint
- Real positions tracking
- Settings wired to agent config

REPLACE: server/app.py
"""
import os, sys, json, time, asyncio, hashlib, threading
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config.settings import CONFIG
from data.pipeline import fetch_data, prepare_multi_stock_data, normalize_features, add_technical_indicators
from env.trading_env import TradingEnv
from agents.ensemble import EnsembleAgent
from sentiment.analyzer import NewsGenerator, TradeExplainer
import numpy as np

# Try loading extra indicators
try:
    from data.indicators import add_extra_indicators, compute_feature_importance
    HAS_EXTRA = True
except ImportError:
    HAS_EXTRA = False

app = FastAPI(title="RL Trading System API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ─── State ─────────────────────────────────────────────────

USERS = {"demo@trader.com": {"id": "user_1", "email": "demo@trader.com", "name": "Demo Trader",
    "password_hash": hashlib.sha256("password123".encode()).hexdigest(), "created_at": "2024-01-01T00:00:00Z"}}
SESSIONS: Dict[str, dict] = {}

profile_data = {"id": "profile_1", "user_id": "user_1", "risk_tolerance": "medium",
    "asset_classes": ["stocks"], "selected_model": "ensemble", "capital_allocation": 1_000_000,
    "max_drawdown": 0.15, "stop_loss_pct": 0.05, "take_profit_pct": 0.15,
    "reward_weights": {"w1": 0.35, "w2": 0.25, "w3": 0.20, "w4": 0.20},
    "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"}

agent_state = {"id": "agent_1", "model": "ensemble", "status": "stopped", "mode": "paper",
    "uptime": 0, "total_signals": 0, "training_status": "not_trained", "training_progress": 0}
portfolio_metrics = {"portfolio_value": 1_000_000, "cash": 1_000_000, "pnl_daily": 0,
    "pnl_cumulative": 0, "pnl_pct": 0, "sharpe_ratio": 0, "sortino_ratio": 0,
    "max_drawdown": 0, "current_drawdown": 0, "win_rate": 0, "total_trades": 0,
    "beta": 1.0, "alpha": 0, "volatility": 0, "timestamp": time.time() * 1000}

market_data_cache: Dict[str, list] = {}
ws_connections: List[WebSocket] = []
engine_running = False
trade_signals: List[dict] = []
system_logs: List[dict] = []
equity_curve: List[dict] = []
positions_state: List[dict] = []
feature_importance_state: Dict[str, float] = {}
cached_data = {"loaded": False, "train": None, "test": None, "tickers": None}
trained_agent = {"agent": None}

# ─── Models ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str; password: str
class SignupRequest(BaseModel):
    name: str; email: str; password: str
class ProfileUpdate(BaseModel):
    risk_tolerance: Optional[str] = None; asset_classes: Optional[List[str]] = None
    selected_model: Optional[str] = None; capital_allocation: Optional[float] = None
    max_drawdown: Optional[float] = None; stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None; reward_weights: Optional[dict] = None
class AgentCommand(BaseModel):
    action: str; model: Optional[str] = None; mode: Optional[str] = None

def create_token(uid):
    t = hashlib.sha256(f"{uid}:s:{time.time()}".encode()).hexdigest()
    SESSIONS[t] = {"user_id": uid, "expires": time.time() + 3600}
    return t

def add_log(level, message, source="system"):
    entry = {"id": f"log_{len(system_logs)}", "level": level, "message": message, "source": source, "timestamp": time.time() * 1000}
    system_logs.append(entry)
    if len(system_logs) > 2000: system_logs.pop(0)

def ok(data): return {"status": "success", "data": data}

# ─── Data ──────────────────────────────────────────────────

def load_data():
    if cached_data["loaded"]: return
    add_log("INFO", f"Loading data for {CONFIG.data.tickers}...", "data")
    raw = fetch_data(CONFIG.data.tickers, CONFIG.data.start_date, CONFIG.data.end_date, CONFIG.data.benchmark)

    # Add extra indicators to raw data before processing
    if HAS_EXTRA:
        for t in list(raw.keys()):
            try:
                raw[t] = add_extra_indicators(raw[t])
                add_log("INFO", f"Added ATR, OBV, Ichimoku, Stochastic to {t}", "data")
            except Exception as e:
                add_log("WARN", f"Extra indicators failed for {t}: {e}", "data")

    sf, bd = prepare_multi_stock_data(raw, CONFIG.data.tickers, CONFIG.data.benchmark)
    norm, _ = normalize_features(sf)
    pc = [c for c in sf.columns if "Close" in c][:len(CONFIG.data.tickers)]
    prices = sf[pc].values; features = norm.values
    bc = "Close" if "Close" in bd.columns else bd.columns[3]
    bv = bd[bc].values
    if hasattr(bv, 'iloc'): bv = bv.values
    bv = bv.flatten()
    br = np.concatenate([[0], np.diff(bv) / bv[:-1]])
    ml = min(len(prices), len(features), len(br))
    prices, features, br = prices[:ml], features[:ml], br[:ml]

    for i, t in enumerate(CONFIG.data.tickers):
        if i < prices.shape[1]:
            market_data_cache[t] = [{"time": j, "open": float(p*0.999), "high": float(p*1.005),
                "low": float(p*0.995), "close": float(p), "volume": 1000000}
                for j, p in enumerate(prices[:, i])]

    sp = int(len(prices) * 0.8)
    cached_data.update({"loaded": True, "tickers": CONFIG.data.tickers,
        "train": {"features": features[:sp], "prices": prices[:sp], "bench_returns": br[:sp]},
        "test": {"features": features[sp:], "prices": prices[sp:], "bench_returns": br[sp:]}})
    add_log("INFO", f"Data: {features.shape[1]} features, {sp} train, {ml-sp} test days", "data")

def make_env(data):
    return TradingEnv(
        stock_data=data["features"], price_data=data["prices"],
        benchmark_returns=data["bench_returns"], tickers=cached_data["tickers"],
        initial_capital=CONFIG.trading.initial_capital,
        transaction_cost=CONFIG.trading.transaction_cost, slippage=CONFIG.trading.slippage,
        max_position_pct=CONFIG.trading.max_position_pct,
        max_drawdown_threshold=CONFIG.trading.max_drawdown_threshold,
        reward_weights=(CONFIG.reward.w1, CONFIG.reward.w2, CONFIG.reward.w3, CONFIG.reward.w4),
        lookback_window=min(30, len(data["prices"]) // 4))

# ─── Training ─────────────────────────────────────────────

TRAIN_EPISODES = 50

def train_agent():
    global trained_agent
    load_data()
    env = make_env(cached_data["train"])
    obs = env.reset()
    agent = EnsembleAgent(obs_dim=len(obs), action_dim=env.action_dim)

    add_log("INFO", f"Training for {TRAIN_EPISODES} episodes (PyTorch: {_has_torch()})...", "training")
    agent_state["training_status"] = "training"
    best = -float("inf")

    for ep in range(TRAIN_EPISODES):
        obs = env.reset(); done = False; er = 0
        while not done:
            a, di = agent.select_action(obs)
            no, r, done, info = env.step(a)
            _, lp, v = agent.ppo.select_action(obs)
            agent.store_transition(obs, a, r, no, done, value=v, log_prob=lp)
            er += r; obs = no
        agent.train()
        p = env.get_performance_summary()
        if er > best: best = er
        agent_state["training_progress"] = int((ep + 1) / TRAIN_EPISODES * 100)

        if (ep + 1) % max(1, TRAIN_EPISODES // 10) == 0 or ep == 0:
            add_log("INFO",
                f"Ep {ep+1}/{TRAIN_EPISODES} | Reward: {er:.0f} | Return: {p.get('total_return',0):.2%} | "
                f"Sharpe: {p.get('sharpe_ratio',0):.3f} | MaxDD: {p.get('max_drawdown',0):.2%}",
                "training")

    trained_agent["agent"] = agent
    agent_state["training_status"] = "trained"
    agent_state["training_progress"] = 100
    add_log("INFO", f"Training complete! Best: {best:.0f}", "training")

def _has_torch():
    try:
        import torch; return True
    except: return False

# ─── Engine ────────────────────────────────────────────────

def run_engine():
    global engine_running, portfolio_metrics, positions_state, feature_importance_state
    try:
        if not trained_agent["agent"]: train_agent()
        agent = trained_agent["agent"]
        load_data()
        env = make_env(cached_data["test"])
        obs = env.reset()
        add_log("INFO", "Paper trading started with trained agent", "agent")
        agent_state["status"] = "running"; agent_state["total_signals"] = 0
        equity_curve.clear()

        ng = NewsGenerator(seed=42)
        done = False; step = 0; t0 = time.time()

        while engine_running and not done:
            a, di = agent.select_action(obs, deterministic=True)
            obs, r, done, info = env.step(a)
            step += 1; pv = info["portfolio_value"]
            p = env.get_performance_summary()

            portfolio_metrics.update({
                "portfolio_value": pv, "cash": info["cash"],
                "pnl_daily": info.get("step_return", 0) * pv,
                "pnl_cumulative": pv - CONFIG.trading.initial_capital,
                "pnl_pct": (pv - CONFIG.trading.initial_capital) / CONFIG.trading.initial_capital,
                "sharpe_ratio": p.get("sharpe_ratio", 0), "sortino_ratio": p.get("sortino_ratio", 0),
                "max_drawdown": p.get("max_drawdown", 0),
                "current_drawdown": getattr(info.get("risk_metrics"), "current_drawdown", 0) if info.get("risk_metrics") else 0,
                "win_rate": p.get("win_rate", 0), "total_trades": p.get("n_trades", 0),
                "beta": p.get("beta", 1.0), "alpha": p.get("alpha", 0),
                "volatility": p.get("volatility", 0), "timestamp": time.time() * 1000})

            # Equity curve
            equity_curve.append({"step": step, "value": round(pv, 2), "timestamp": time.time() * 1000})

            # Positions
            positions_state.clear()
            if hasattr(env, 'positions') and hasattr(env, 'price_data'):
                curr_prices = env.price_data[min(env.current_step, len(env.price_data) - 1)]
                for i, ticker in enumerate(CONFIG.data.tickers):
                    if i < len(env.positions) and abs(env.positions[i]) > 0.01:
                        shares = env.positions[i]
                        price = float(curr_prices[i]) if i < len(curr_prices) else 0
                        positions_state.append({
                            "symbol": ticker, "shares": round(float(shares), 2),
                            "current_price": round(price, 2),
                            "market_value": round(float(shares) * price, 2),
                            "weight": round(abs(float(shares) * price) / max(pv, 1) * 100, 1),
                        })

            # Trade signals
            for t in info.get("trades", []):
                idx = CONFIG.data.tickers.index(t["ticker"]) if t["ticker"] in CONFIG.data.tickers else 0
                sig = {"id": f"sig_{len(trade_signals)}", "symbol": t["ticker"], "action": t["action"],
                    "confidence": round(min(0.95, 0.5 + abs(a[idx]) * 0.4), 2),
                    "price": round(t["price"], 2), "quantity": round(t["shares"], 2),
                    "timestamp": time.time() * 1000,
                    "reasoning": f"{t['action']} {t['ticker']}",
                    "regime": info.get("regime", "sideways").lower().replace(" ", "_")}
                trade_signals.append(sig)
                agent_state["total_signals"] = len(trade_signals)

            # Feature importance (every 30 steps)
            if step % 30 == 0 and HAS_EXTRA:
                try:
                    feat_names = [f"f{i}" for i in range(len(obs))]
                    fi = compute_feature_importance(obs, feat_names, agent.ppo, n_perturbations=5)
                    feature_importance_state.clear()
                    feature_importance_state.update(fi)
                except: pass

            # Logging
            if step % 5 == 0:
                pnl = pv - CONFIG.trading.initial_capital
                add_log("INFO", f"Step {step} | ${pv:,.0f} ({'+' if pnl>=0 else ''}{pnl:,.0f}) | {info.get('regime','?')} | {len(info.get('trades',[]))} trades", "agent")

            if step % 25 == 0:
                news = ng.generate_news(CONFIG.data.tickers[:2], 1, info.get("regime", "Sideways"))
                if news: add_log("INFO", f"Sentiment: {news[0].ticker} {news[0].sentiment} — {news[0].title[:50]}", "sentiment")

            agent_state["uptime"] = int(time.time() - t0)
            time.sleep(0.2)

        agent_state["status"] = "stopped"
        f = env.get_performance_summary()
        add_log("INFO", f"Done | ${pv:,.0f} | Return: {f.get('total_return',0):.2%} | Sharpe: {f.get('sharpe_ratio',0):.3f}", "engine")
    except Exception as e:
        agent_state["status"] = "error"
        add_log("ERROR", str(e), "engine")
        import traceback; traceback.print_exc()

# ─── REST ──────────────────────────────────────────────────

@app.post("/api/v1/auth/login")
async def login(req: LoginRequest):
    u = USERS.get(req.email)
    if not u or hashlib.sha256(req.password.encode()).hexdigest() != u["password_hash"]:
        raise HTTPException(401, "Invalid credentials")
    return ok({"accessToken": create_token(u["id"]), "user": {"id": u["id"], "email": u["email"], "name": u["name"], "createdAt": u["created_at"]}})

@app.post("/api/v1/auth/signup")
async def signup(req: SignupRequest):
    if req.email in USERS: raise HTTPException(400, "Email exists")
    uid = f"user_{len(USERS)+1}"
    USERS[req.email] = {"id": uid, "email": req.email, "name": req.name, "password_hash": hashlib.sha256(req.password.encode()).hexdigest(), "created_at": datetime.utcnow().isoformat()+"Z"}
    return ok({"accessToken": create_token(uid), "user": {"id": uid, "email": req.email, "name": req.name}})

@app.post("/api/v1/auth/refresh")
async def refresh(): return ok({"accessToken": create_token("user_1")})

@app.get("/api/v1/auth/me")
async def get_me(): return ok({"id": "user_1", "email": "demo@trader.com", "name": "Demo Trader", "createdAt": "2024-01-01T00:00:00Z"})

@app.get("/api/v1/profile")
async def get_profile(): return ok(profile_data)

@app.patch("/api/v1/profile")
async def update_profile(req: ProfileUpdate):
    u = req.model_dump(exclude_none=True)
    profile_data.update(u)
    profile_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    if "reward_weights" in u:
        w = u["reward_weights"]
        CONFIG.reward.w1 = w.get("w1", CONFIG.reward.w1); CONFIG.reward.w2 = w.get("w2", CONFIG.reward.w2)
        CONFIG.reward.w3 = w.get("w3", CONFIG.reward.w3); CONFIG.reward.w4 = w.get("w4", CONFIG.reward.w4)
    if "max_drawdown" in u: CONFIG.trading.max_drawdown_threshold = u["max_drawdown"]
    if "stop_loss_pct" in u: CONFIG.trading.stop_loss_pct = u["stop_loss_pct"]
    if "take_profit_pct" in u: CONFIG.trading.take_profit_pct = u["take_profit_pct"]
    add_log("INFO", f"Profile updated: {list(u.keys())}", "config")
    return ok(profile_data)

@app.get("/api/v1/agents/status")
async def get_status(): return ok([agent_state])

@app.post("/api/v1/agents/control")
async def control(cmd: AgentCommand):
    global engine_running
    if cmd.action == "start":
        if agent_state["status"] == "running": raise HTTPException(400, "Already running")
        engine_running = True
        if cmd.model: agent_state["model"] = cmd.model
        if cmd.mode: agent_state["mode"] = cmd.mode
        threading.Thread(target=run_engine, daemon=True).start()
        return ok({"message": "Starting (trains first if needed)", "state": agent_state})
    elif cmd.action == "stop":
        engine_running = False; agent_state["status"] = "stopped"
        add_log("INFO", "Agent stopped", "agent"); return ok({"message": "Stopped"})
    raise HTTPException(400, f"Unknown: {cmd.action}")

@app.get("/api/v1/portfolio/metrics")
async def metrics(): return ok(portfolio_metrics)

@app.get("/api/v1/portfolio/positions")
async def positions(): return ok(positions_state)

@app.get("/api/v1/portfolio/trades")
async def trades(): return ok(trade_signals[-100:])

@app.get("/api/v1/portfolio/equity")
async def equity(): return ok(equity_curve[-500:])

@app.get("/api/v1/portfolio/feature_importance")
async def feat_imp(): return ok(feature_importance_state)

@app.get("/api/v1/market/symbols")
async def symbols(): return ok(CONFIG.data.tickers)

@app.get("/api/v1/market/history/{symbol}")
async def history(symbol: str):
    if not market_data_cache:
        try: load_data()
        except: pass
    return ok(market_data_cache.get(symbol, [])[-500:])

@app.get("/api/v1/logs")
async def logs(level: str = "ALL", limit: int = 100):
    if level == "ALL": return ok(system_logs[-limit:])
    return ok([l for l in system_logs if l["level"] == level][-limit:])

@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept(); ws_connections.append(ws)
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        if ws in ws_connections: ws_connections.remove(ws)

@app.on_event("startup")
async def startup():
    add_log("INFO", "RL Trading System API v3.0", "system")
    add_log("INFO", f"Assets: {CONFIG.data.tickers} | PyTorch: {_has_torch()}", "system")
    add_log("INFO", f"Training: {TRAIN_EPISODES} episodes | Extra indicators: {HAS_EXTRA}", "system")

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════╗")
    print("║  RL Trading System API v3.0                        ║")
    print("║  http://localhost:8000/docs                        ║")
    print("║  Login: demo@trader.com / password123              ║")
    print(f"║  PyTorch: {_has_torch()} | Extra indicators: {HAS_EXTRA}        ║")
    print(f"║  Training episodes: {TRAIN_EPISODES}                            ║")
    print("╚════════════════════════════════════════════════════╝")
    uvicorn.run(app, host="0.0.0.0", port=8000)