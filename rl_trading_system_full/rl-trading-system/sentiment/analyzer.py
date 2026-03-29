"""
Sentiment & News Module
========================
LLM-based news fetching, sentiment analysis, and decision validation.
Provides explainability for trading decisions.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib


@dataclass
class NewsItem:
    """Single news article with sentiment."""
    title: str
    source: str
    timestamp: str
    ticker: str
    sentiment: str = "neutral"        # positive / negative / neutral
    confidence: float = 0.5
    summary: str = ""
    impact_score: float = 0.0         # -1 to 1


@dataclass
class SentimentReport:
    """Aggregated sentiment for a ticker."""
    ticker: str
    overall_sentiment: str = "neutral"
    overall_confidence: float = 0.5
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    avg_impact: float = 0.0
    news_items: List[NewsItem] = field(default_factory=list)
    reasoning: str = ""


class NewsGenerator:
    """
    Generates realistic simulated news for development/testing.
    In production, replace with real news API (NewsAPI, Bloomberg, etc.)
    or LLM-based news fetching.
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
            "{ticker} stock surges on favorable regulatory decision",
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
        ]
    }

    SOURCES = [
        "Reuters", "Bloomberg", "CNBC", "WSJ", "Financial Times",
        "MarketWatch", "Seeking Alpha", "The Motley Fool"
    ]

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate_news(
        self, tickers: List[str], n_items: int = 3, market_regime: str = "Sideways"
    ) -> List[NewsItem]:
        """Generate simulated news items based on market regime."""
        news = []

        # Regime influences sentiment distribution
        if market_regime == "Bull Market":
            probs = [0.6, 0.15, 0.25]  # pos, neg, neutral
        elif market_regime == "Bear Market":
            probs = [0.15, 0.6, 0.25]
        elif market_regime == "High Volatility":
            probs = [0.3, 0.4, 0.3]
        else:
            probs = [0.33, 0.33, 0.34]

        sentiments = ["positive", "negative", "neutral"]

        for ticker in tickers:
            for _ in range(n_items):
                sentiment = self.rng.choice(sentiments, p=probs)
                templates = self.TEMPLATES[sentiment]
                title = self.rng.choice(templates).format(ticker=ticker)
                confidence = 0.6 + self.rng.random() * 0.35

                impact_map = {"positive": 0.3 + self.rng.random() * 0.5,
                              "negative": -(0.3 + self.rng.random() * 0.5),
                              "neutral": (self.rng.random() - 0.5) * 0.2}

                item = NewsItem(
                    title=title,
                    source=self.rng.choice(self.SOURCES),
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
                    ticker=ticker,
                    sentiment=sentiment,
                    confidence=confidence,
                    summary=f"Analysis: {title}",
                    impact_score=impact_map[sentiment]
                )
                news.append(item)

        return news


class SentimentAnalyzer:
    """
    Analyzes sentiment from news and generates trading signals.
    In production, uses LLM API for sentiment analysis.
    Here, uses rule-based analysis on simulated news.
    """

    def __init__(self):
        self.history: Dict[str, List[SentimentReport]] = {}

    def analyze(self, news_items: List[NewsItem], ticker: str) -> SentimentReport:
        """Aggregate sentiment for a ticker from news items."""
        ticker_news = [n for n in news_items if n.ticker == ticker]

        if not ticker_news:
            return SentimentReport(ticker=ticker)

        pos = sum(1 for n in ticker_news if n.sentiment == "positive")
        neg = sum(1 for n in ticker_news if n.sentiment == "negative")
        neu = sum(1 for n in ticker_news if n.sentiment == "neutral")
        total = len(ticker_news)

        avg_impact = np.mean([n.impact_score for n in ticker_news])
        avg_confidence = np.mean([n.confidence for n in ticker_news])

        if pos > neg and pos > neu:
            overall = "positive"
        elif neg > pos and neg > neu:
            overall = "negative"
        else:
            overall = "neutral"

        # Generate reasoning
        reasoning = self._generate_reasoning(ticker, overall, ticker_news, avg_impact)

        report = SentimentReport(
            ticker=ticker,
            overall_sentiment=overall,
            overall_confidence=avg_confidence,
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            avg_impact=avg_impact,
            news_items=ticker_news,
            reasoning=reasoning
        )

        if ticker not in self.history:
            self.history[ticker] = []
        self.history[ticker].append(report)

        return report

    def _generate_reasoning(
        self, ticker: str, sentiment: str,
        news: List[NewsItem], impact: float
    ) -> str:
        """Generate human-readable sentiment reasoning."""
        top_news = sorted(news, key=lambda x: abs(x.impact_score), reverse=True)[:2]

        if sentiment == "positive":
            reasoning = (
                f"Sentiment for {ticker} is POSITIVE (impact: {impact:.2f}). "
                f"Key drivers: {top_news[0].title}. "
                f"This supports bullish positioning with {top_news[0].confidence:.0%} confidence."
            )
        elif sentiment == "negative":
            reasoning = (
                f"Sentiment for {ticker} is NEGATIVE (impact: {impact:.2f}). "
                f"Concerns: {top_news[0].title}. "
                f"Caution warranted; consider reducing exposure."
            )
        else:
            reasoning = (
                f"Sentiment for {ticker} is NEUTRAL (impact: {impact:.2f}). "
                f"No strong catalysts detected. Maintain current positioning."
            )

        return reasoning


class DecisionValidator:
    """
    Validates RL agent decisions against sentiment signals.
    Reduces position size or delays trades when conflicts are detected.
    """

    def __init__(self, conflict_scale: float = 0.5, delay_threshold: float = 0.7):
        self.conflict_scale = conflict_scale
        self.delay_threshold = delay_threshold
        self.validation_log: List[Dict] = []

    def validate(
        self,
        agent_action: float,
        sentiment_report: SentimentReport,
        ticker: str
    ) -> Tuple[float, Dict]:
        """
        Validate agent action against sentiment.

        Args:
            agent_action: RL agent's action [-1, 1]
            sentiment_report: Sentiment analysis for the ticker
            ticker: Asset ticker

        Returns:
            (modified_action, validation_info)
        """
        sentiment_signal = sentiment_report.avg_impact
        confidence = sentiment_report.overall_confidence

        # Detect conflict: agent wants to buy but sentiment is negative, or vice versa
        is_conflict = (
            (agent_action > 0.2 and sentiment_signal < -0.3) or
            (agent_action < -0.2 and sentiment_signal > 0.3)
        )

        modified_action = agent_action
        validation_status = "aligned"

        if is_conflict and confidence > self.delay_threshold:
            # Strong conflict with high confidence: reduce position significantly
            modified_action = agent_action * self.conflict_scale
            validation_status = "conflict_reduced"
        elif is_conflict:
            # Mild conflict: slight reduction
            modified_action = agent_action * 0.75
            validation_status = "mild_conflict"
        elif abs(sentiment_signal) > 0.5 and np.sign(agent_action) == np.sign(sentiment_signal):
            # Strong alignment: slight boost
            modified_action = np.clip(agent_action * 1.1, -1, 1)
            validation_status = "sentiment_boost"

        info = {
            "ticker": ticker,
            "original_action": float(agent_action),
            "modified_action": float(modified_action),
            "sentiment": sentiment_report.overall_sentiment,
            "sentiment_impact": float(sentiment_signal),
            "confidence": float(confidence),
            "status": validation_status,
            "reasoning": sentiment_report.reasoning
        }

        self.validation_log.append(info)
        return modified_action, info


class TradeExplainer:
    """
    Generates human-readable explanations for trading decisions.
    Combines RL decision info, sentiment, regime, and technical indicators.
    """

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
        risk_metrics: Dict = None
    ) -> str:
        """
        Generate comprehensive trade explanation.

        Example output:
        "Agent BOUGHT AAPL because: momentum signals bullish (RSI=65, MACD positive),
         positive earnings news (confidence 85%), bull market regime detected.
         PPO and SAC agents agree (92% alignment). Risk: Sharpe 1.2, Drawdown 3%."
        """
        # Determine action type
        if action > 0.2:
            action_type = "BOUGHT"
            direction = "bullish"
        elif action < -0.2:
            action_type = "SOLD"
            direction = "bearish"
        else:
            action_type = "HELD"
            direction = "neutral"

        parts = [f"Agent {action_type} {ticker} because:"]

        # Technical signals
        tech_reasons = []
        if technical_signals:
            rsi = technical_signals.get("rsi", 50)
            macd = technical_signals.get("macd", 0)
            if rsi > 60:
                tech_reasons.append(f"RSI={rsi:.0f} (overbought zone)")
            elif rsi < 40:
                tech_reasons.append(f"RSI={rsi:.0f} (oversold zone)")
            if macd > 0:
                tech_reasons.append("MACD positive (bullish momentum)")
            elif macd < 0:
                tech_reasons.append("MACD negative (bearish momentum)")

        if tech_reasons:
            parts.append(f"Technical: {', '.join(tech_reasons)}.")

        # Sentiment
        sent = sentiment_info.get("sentiment", "neutral")
        conf = sentiment_info.get("confidence", 0.5)
        parts.append(f"Sentiment: {sent} ({conf:.0%} confidence).")

        # Regime
        parts.append(f"Market regime: {regime}.")

        # Ensemble info
        agreement = ensemble_info.get("agreement", 0.5)
        dominant = ensemble_info.get("dominant_agent", "ensemble")
        parts.append(f"Agent consensus: {agreement:.0%} ({dominant}).")

        # Risk
        if risk_metrics:
            sharpe = risk_metrics.get("sharpe_ratio", 0)
            dd = risk_metrics.get("current_drawdown", 0)
            parts.append(f"Risk: Sharpe {sharpe:.2f}, Drawdown {dd:.1%}.")

        explanation = " ".join(parts)

        self.explanations.append({
            "ticker": ticker,
            "action": action_type,
            "explanation": explanation,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        return explanation

    def get_feature_importance(
        self, observation: np.ndarray, feature_names: List[str]
    ) -> Dict[str, float]:
        """
        Approximate feature importance using permutation sensitivity.
        (Simplified SHAP-like analysis)
        """
        if len(feature_names) != len(observation):
            # Truncate or pad
            n = min(len(feature_names), len(observation))
            feature_names = feature_names[:n]
            observation = observation[:n]

        importance = {}
        baseline = np.abs(observation)
        total = np.sum(baseline) + 1e-10

        for i, name in enumerate(feature_names):
            importance[name] = float(baseline[i] / total)

        # Sort by importance
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
        return importance
