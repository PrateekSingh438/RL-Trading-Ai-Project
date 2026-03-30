"""
Sentiment & News Module v2
==========================
Fetches REAL news via yfinance + keyword-based sentiment scoring.
Falls back to template-based simulation when live fetch fails.

Key classes
-----------
LiveNewsFetcher   – real headlines from yfinance + keyword VADER scorer
NewsGenerator     – template simulation (fallback / testing)
SentimentAnalyzer – aggregates NewsItem lists into SentimentReport
DecisionValidator – adjusts RL action based on sentiment
TradeExplainer    – human-readable trade reasoning
"""
import time
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    title: str
    source: str
    timestamp: str
    ticker: str
    sentiment: str = "neutral"       # positive / negative / neutral
    confidence: float = 0.5
    summary: str = ""
    impact_score: float = 0.0        # -1 to +1
    url: str = ""
    is_live: bool = False            # True = fetched from real API


@dataclass
class SentimentReport:
    ticker: str
    overall_sentiment: str = "neutral"
    overall_confidence: float = 0.5
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_impact: float = 0.0
    news_items: List[NewsItem] = field(default_factory=list)
    reasoning: str = ""
    live_data: bool = False          # True if at least one real headline


# ─── Keyword scorer ───────────────────────────────────────────────────────────

_POS_KW = {
    "surge", "soar", "rally", "beat", "record", "profit", "gain", "rise", "jump",
    "strong", "growth", "upgrade", "outperform", "buy", "bullish", "positive",
    "exceed", "breakthrough", "success", "expand", "partnership", "approval",
    "dividend", "innovative", "launch", "acquisition", "boost", "recover",
    "revenue", "earnings beat", "raised guidance", "upbeat", "optimistic",
}
_NEG_KW = {
    "drop", "plunge", "fall", "crash", "miss", "loss", "decline", "weak", "down",
    "downgrade", "underperform", "sell", "bearish", "negative", "concern", "warn",
    "cut", "lawsuit", "investigation", "risk", "layoff", "restructure", "debt",
    "recall", "fraud", "violation", "penalty", "slump", "shortfall", "delay",
    "miss estimates", "lowered guidance", "disappointing",
}


def _keyword_score(text: str) -> Tuple[str, float, float]:
    """
    Returns (sentiment, confidence, impact_score) from raw text.
    """
    tl = text.lower()
    pos = sum(1 for kw in _POS_KW if kw in tl)
    neg = sum(1 for kw in _NEG_KW if kw in tl)
    total = pos + neg
    if total == 0:
        return "neutral", 0.45, 0.0
    pos_r = pos / total
    if pos_r >= 0.6:
        sent = "positive"
        impact = round(0.3 + pos_r * 0.6, 3)
    elif pos_r <= 0.4:
        sent = "negative"
        impact = round(-(0.3 + (1 - pos_r) * 0.6), 3)
    else:
        sent = "neutral"
        impact = round((pos_r - 0.5) * 0.4, 3)
    conf = min(0.95, 0.50 + abs(pos_r - 0.5) * 1.0)
    return sent, round(conf, 3), impact


# ─── Live news fetcher ────────────────────────────────────────────────────────

class LiveNewsFetcher:
    """
    Fetches real financial headlines from yfinance and scores them with
    a keyword-based sentiment analyser.  Results are cached per-ticker
    for `cache_ttl` seconds (default 300 s = 5 min) so we don't hammer
    the API on every training step.
    """

    def __init__(self, cache_ttl: int = 300):
        self._cache: Dict[str, Tuple[List[NewsItem], float]] = {}
        self.cache_ttl = cache_ttl
        self._yf_available = None   # None = not yet checked

    def _check_yf(self) -> bool:
        if self._yf_available is None:
            try:
                import yfinance  # noqa: F401
                self._yf_available = True
            except ImportError:
                self._yf_available = False
        return self._yf_available

    def fetch(self, ticker: str, max_items: int = 10) -> List[NewsItem]:
        """
        Return up to `max_items` live NewsItems for `ticker`.
        Returns [] on any failure (caller should fall back to simulation).
        """
        now = time.time()
        cached_items, ts = self._cache.get(ticker, ([], 0.0))
        if cached_items and (now - ts) < self.cache_ttl:
            return cached_items

        if not self._check_yf():
            return []

        try:
            import yfinance as yf
            tk = yf.Ticker(ticker)
            raw = tk.news or []
            items: List[NewsItem] = []
            for article in raw[:max_items]:
                title = article.get("title", "")
                if not title:
                    continue
                source = article.get("publisher", "Yahoo Finance")
                pub_ts = article.get("providerPublishTime", int(now))
                url = article.get("link", "")
                summary = article.get("summary", title)
                sentiment, confidence, impact = _keyword_score(title + " " + summary)
                items.append(NewsItem(
                    title=title,
                    source=source,
                    timestamp=datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M"),
                    ticker=ticker,
                    sentiment=sentiment,
                    confidence=confidence,
                    summary=summary[:200],
                    impact_score=impact,
                    url=url,
                    is_live=True,
                ))
            self._cache[ticker] = (items, now)
            return items
        except Exception:
            return []

    def fetch_many(self, tickers: List[str]) -> List[NewsItem]:
        """Fetch live news for multiple tickers, merge results."""
        out: List[NewsItem] = []
        for t in tickers:
            out.extend(self.fetch(t))
        return out

    def invalidate(self, ticker: str = None):
        """Clear cache for one ticker or all tickers."""
        if ticker:
            self._cache.pop(ticker, None)
        else:
            self._cache.clear()


# ─── Template-based simulator (fallback) ─────────────────────────────────────

class NewsGenerator:
    """
    Generates realistic simulated news (development / fallback only).
    """

    TEMPLATES = {
        "positive": [
            "{ticker} reports record quarterly earnings, beating estimates by 15%",
            "{ticker} announces major partnership with leading tech firm",
            "{ticker} receives analyst upgrade to 'Strong Buy'",
            "Institutional investors increase stake in {ticker} by 8%",
            "{ticker} launches innovative product line to strong market reception",
            "{ticker} beats revenue expectations, raises full-year guidance",
            "CEO of {ticker} announces ambitious AI integration strategy",
            "{ticker} stock surges on favourable regulatory decision",
        ],
        "negative": [
            "{ticker} misses earnings estimates, shares drop in after-hours",
            "{ticker} faces antitrust investigation from federal regulators",
            "Analyst downgrades {ticker} citing competitive headwinds",
            "{ticker} announces layoffs affecting 5% of workforce",
            "Supply chain disruptions impact {ticker} production targets",
            "{ticker} warns of slowing growth in key market segment",
            "Insider selling detected at {ticker}, raises investor concerns",
            "{ticker} faces class-action lawsuit over product issues",
        ],
        "neutral": [
            "{ticker} CEO speaks at industry conference on future outlook",
            "{ticker} to release quarterly results next week",
            "Market analysts maintain 'Hold' rating on {ticker}",
            "{ticker} completes routine corporate restructuring",
            "Trading volume in {ticker} remains near 30-day average",
            "{ticker} files new patent applications in emerging technology",
        ],
    }
    SOURCES = ["Reuters", "Bloomberg", "CNBC", "WSJ", "Financial Times",
               "MarketWatch", "Seeking Alpha", "The Motley Fool"]

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate_news(
        self, tickers: List[str], n_items: int = 3, market_regime: str = "Sideways"
    ) -> List[NewsItem]:
        regime_probs = {
            "Bull Market":     [0.60, 0.15, 0.25],
            "Bear Market":     [0.15, 0.60, 0.25],
            "High Volatility": [0.30, 0.40, 0.30],
        }
        probs = regime_probs.get(market_regime, [0.33, 0.33, 0.34])
        sentiments = ["positive", "negative", "neutral"]
        news = []
        for ticker in tickers:
            for _ in range(n_items):
                sent = self.rng.choice(sentiments, p=probs)
                title = self.rng.choice(self.TEMPLATES[sent]).format(ticker=ticker)
                conf = float(0.60 + self.rng.random() * 0.35)
                impact_map = {
                    "positive":  float(0.3 + self.rng.random() * 0.5),
                    "negative": -float(0.3 + self.rng.random() * 0.5),
                    "neutral":   float((self.rng.random() - 0.5) * 0.2),
                }
                news.append(NewsItem(
                    title=title,
                    source=self.rng.choice(self.SOURCES),
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    ticker=ticker,
                    sentiment=sent,
                    confidence=conf,
                    summary=f"Analysis: {title}",
                    impact_score=impact_map[sent],
                    is_live=False,
                ))
        return news


# ─── Sentiment analyser ───────────────────────────────────────────────────────

class SentimentAnalyzer:
    """
    Aggregates a list of NewsItems into a SentimentReport for a ticker.
    Prefers live items; falls back to simulated when none present.
    """

    def __init__(self):
        self.history: Dict[str, List[SentimentReport]] = {}
        self.live_fetcher = LiveNewsFetcher()
        self._fallback_gen = NewsGenerator()

    def get_live_report(
        self, ticker: str, regime: str = "Sideways"
    ) -> SentimentReport:
        """
        Convenience: fetch live news for `ticker` and return a SentimentReport.
        Automatically falls back to simulated if live fetch returns nothing.
        """
        items = self.live_fetcher.fetch(ticker)
        if not items:
            items = self._fallback_gen.generate_news([ticker], n_items=3,
                                                     market_regime=regime)
        return self.analyze(items, ticker)

    def analyze(self, news_items: List[NewsItem], ticker: str) -> SentimentReport:
        ticker_news = [n for n in news_items if n.ticker == ticker]
        if not ticker_news:
            return SentimentReport(ticker=ticker)

        pos = sum(1 for n in ticker_news if n.sentiment == "positive")
        neg = sum(1 for n in ticker_news if n.sentiment == "negative")
        neu = sum(1 for n in ticker_news if n.sentiment == "neutral")

        avg_impact = float(np.mean([n.impact_score for n in ticker_news]))
        avg_conf   = float(np.mean([n.confidence   for n in ticker_news]))
        live_data  = any(n.is_live for n in ticker_news)

        if pos > neg and pos > neu:
            overall = "positive"
        elif neg > pos and neg > neu:
            overall = "negative"
        else:
            overall = "neutral"

        reasoning = self._make_reasoning(ticker, overall, ticker_news, avg_impact)
        report = SentimentReport(
            ticker=ticker,
            overall_sentiment=overall,
            overall_confidence=avg_conf,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            avg_impact=avg_impact,
            news_items=ticker_news,
            reasoning=reasoning,
            live_data=live_data,
        )
        self.history.setdefault(ticker, []).append(report)
        return report

    def _make_reasoning(
        self, ticker: str, sentiment: str,
        news: List[NewsItem], impact: float
    ) -> str:
        top = sorted(news, key=lambda x: abs(x.impact_score), reverse=True)[:2]
        live_tag = " [LIVE]" if any(n.is_live for n in top) else ""
        if sentiment == "positive":
            return (
                f"Sentiment for {ticker} is POSITIVE{live_tag} (impact {impact:+.2f}). "
                f"Key driver: {top[0].title}. "
                f"Confidence {top[0].confidence:.0%} → supports bullish positioning."
            )
        if sentiment == "negative":
            return (
                f"Sentiment for {ticker} is NEGATIVE{live_tag} (impact {impact:+.2f}). "
                f"Concern: {top[0].title}. "
                f"Caution warranted; consider reducing exposure."
            )
        return (
            f"Sentiment for {ticker} is NEUTRAL{live_tag} (impact {impact:+.2f}). "
            f"No strong catalyst detected. Maintain current positioning."
        )


# ─── Decision validator ───────────────────────────────────────────────────────

class DecisionValidator:
    """
    Validates RL agent actions against sentiment and adjusts position size.
    Live sentiment (higher-quality signal) is given a small extra weight.
    """

    def __init__(self, conflict_scale: float = 0.5, delay_threshold: float = 0.65):
        self.conflict_scale = conflict_scale
        self.delay_threshold = delay_threshold
        self.validation_log: List[Dict] = []

    def validate(
        self,
        agent_action: float,
        sentiment_report: SentimentReport,
        ticker: str,
    ) -> Tuple[float, Dict]:
        signal = sentiment_report.avg_impact
        conf = sentiment_report.overall_confidence
        # Live data → trust the signal a bit more
        if sentiment_report.live_data:
            conf = min(0.95, conf * 1.10)

        conflict = (
            (agent_action > 0.20 and signal < -0.30) or
            (agent_action < -0.20 and signal > 0.30)
        )
        modified = agent_action
        status = "aligned"

        if conflict and conf > self.delay_threshold:
            modified = agent_action * self.conflict_scale
            status = "conflict_reduced"
        elif conflict:
            modified = agent_action * 0.80
            status = "mild_conflict"
        elif abs(signal) > 0.45 and np.sign(agent_action) == np.sign(signal):
            modified = float(np.clip(agent_action * 1.10, -1.0, 1.0))
            status = "sentiment_boost"

        info = {
            "ticker": ticker,
            "original_action": float(agent_action),
            "modified_action": float(modified),
            "sentiment": sentiment_report.overall_sentiment,
            "sentiment_impact": float(signal),
            "confidence": float(conf),
            "status": status,
            "live_data": sentiment_report.live_data,
            "reasoning": sentiment_report.reasoning,
        }
        self.validation_log.append(info)
        return modified, info


# ─── Trade explainer ─────────────────────────────────────────────────────────

class TradeExplainer:
    """Generates human-readable explanations for trading decisions."""

    def __init__(self):
        self.explanations: List[Dict] = []

    def explain(
        self,
        ticker: str,
        action: float,
        ensemble_info: Dict,
        sentiment_info: Dict,
        regime: str,
        technical_signals: Dict,
        risk_metrics: Dict = None,
    ) -> str:
        if action > 0.20:
            action_type, direction = "BOUGHT", "bullish"
        elif action < -0.20:
            action_type, direction = "SOLD", "bearish"
        else:
            action_type, direction = "HELD", "neutral"

        parts = [f"Agent {action_type} {ticker}:"]

        tech = []
        rsi  = technical_signals.get("rsi", 50)
        macd = technical_signals.get("macd", 0)
        if rsi > 60:
            tech.append(f"RSI={rsi:.0f} overbought")
        elif rsi < 40:
            tech.append(f"RSI={rsi:.0f} oversold")
        if macd > 0:
            tech.append("MACD+ bullish")
        elif macd < 0:
            tech.append("MACD- bearish")
        if tech:
            parts.append(f"Tech [{', '.join(tech)}].")

        sent  = sentiment_info.get("sentiment", "neutral")
        conf  = sentiment_info.get("confidence", 0.5)
        live  = sentiment_info.get("live_data", False)
        parts.append(f"Sentiment: {sent} ({conf:.0%} conf{'  LIVE' if live else ''}).")
        parts.append(f"Regime: {regime}.")

        agreement = ensemble_info.get("agreement", 0.5)
        dominant  = ensemble_info.get("dominant_agent", "ensemble")
        parts.append(f"Consensus: {agreement:.0%} ({dominant}).")

        if risk_metrics:
            sharpe = risk_metrics.get("sharpe_ratio", 0)
            dd     = risk_metrics.get("current_drawdown", 0)
            parts.append(f"Risk: Sharpe {sharpe:.2f}, DD {dd:.1%}.")

        explanation = " ".join(parts)
        self.explanations.append({
            "ticker": ticker,
            "action": action_type,
            "explanation": explanation,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return explanation

    def get_feature_importance(
        self, observation: np.ndarray, feature_names: List[str]
    ) -> Dict[str, float]:
        n = min(len(feature_names), len(observation))
        feature_names = feature_names[:n]
        observation   = observation[:n]
        baseline = np.abs(observation)
        total    = np.sum(baseline) + 1e-10
        imp = {name: float(baseline[i] / total)
               for i, name in enumerate(feature_names)}
        return dict(sorted(imp.items(), key=lambda x: x[1], reverse=True))
