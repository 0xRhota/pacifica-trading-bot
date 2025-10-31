"""
Macro Context Fetcher
Fetches and caches macro market context data for LLM prompts
Refreshes every 12 hours to provide "big picture" market state

Usage:
    fetcher = MacroContextFetcher()
    macro_context = fetcher.get_macro_context()  # Returns cached or fetches fresh
"""

import requests
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class MacroContextFetcher:
    """Fetch and cache macro market context for LLM trading agent"""

    def __init__(self, cambrian_api_key: str, refresh_interval_hours: int = 12):
        """
        Args:
            cambrian_api_key: Cambrian API key for Deep42
            refresh_interval_hours: How often to refresh macro context (default: 12 hours)
        """
        self.cambrian_api_key = cambrian_api_key
        self.refresh_interval = timedelta(hours=refresh_interval_hours)

        # Cache
        self._cached_context: Optional[str] = None
        self._last_fetch: Optional[datetime] = None

    def _should_refresh(self) -> bool:
        """Check if cache should be refreshed"""
        if self._cached_context is None or self._last_fetch is None:
            return True

        time_since_fetch = datetime.now() - self._last_fetch
        return time_since_fetch >= self.refresh_interval

    def _fetch_deep42_analysis(self, question: Optional[str] = None) -> Optional[str]:
        """
        Fetch Deep42 market analysis

        Args:
            question: Optional custom question. If None, uses default broad analysis.
        """
        try:
            url = "https://deep42.cambrian.network/api/v1/deep42/agents/deep42"

            # Default question if not provided
            if question is None:
                question = "What is the current state of the crypto market?"
            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }
            # Use custom question or default
            params = {"question": question}

            response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                return data.get("answer")
            else:
                logger.warning(f"Deep42 fetch failed: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Deep42 fetch error: {e}")
            return None

    def _fetch_deep42_multi_analysis(self) -> Dict[str, Optional[str]]:
        """
        Fetch multiple Deep42 analyses for granular context

        Returns:
            Dict with keys: 'daily', 'weekly', 'market_state'
        """
        today = datetime.now().strftime("%A, %B %d, %Y")

        questions = {
            "market_state": "What is the current state of the crypto market? Focus on Bitcoin and major altcoins sentiment.",
            "daily": f"What are the major cryptocurrency news, catalysts, and events happening TODAY ({today})? Include any significant token launches, protocol updates, or market-moving announcements.",
            "weekly": f"What are the key crypto events and catalysts expected THIS WEEK (week of {today})? Include scheduled updates, launches, or important dates."
        }

        results = {}
        for key, question in questions.items():
            logger.info(f"Fetching Deep42: {key}...")
            results[key] = self._fetch_deep42_analysis(question)
            time.sleep(1)  # Rate limit between requests

        return results

    def _fetch_coingecko_metrics(self) -> Optional[Dict]:
        """Fetch CoinGecko global metrics"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
            if response.status_code == 200:
                data = response.json()["data"]
                return {
                    "market_cap_usd": data["total_market_cap"]["usd"],
                    "volume_24h_usd": data["total_volume"]["usd"],
                    "btc_dominance": data["market_cap_percentage"]["btc"],
                    "eth_dominance": data["market_cap_percentage"]["eth"],
                    "market_cap_change_24h": data["market_cap_change_percentage_24h_usd"]
                }
            return None
        except Exception as e:
            logger.error(f"CoinGecko fetch error: {e}")
            return None

    def _fetch_fear_greed_index(self) -> Optional[Dict]:
        """Fetch Fear & Greed Index"""
        try:
            response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            if response.status_code == 200:
                data = response.json()["data"][0]
                return {
                    "value": int(data["value"]),
                    "classification": data["value_classification"]
                }
            return None
        except Exception as e:
            logger.error(f"Fear & Greed fetch error: {e}")
            return None

    def _format_macro_context(
        self,
        deep42_analysis: Optional[str],
        cg_metrics: Optional[Dict],
        fg_index: Optional[Dict]
    ) -> str:
        """Format macro context for LLM prompt"""

        sections = []

        # Header
        sections.append("=" * 70)
        sections.append("MACRO CONTEXT (Market State)")
        sections.append(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        sections.append("=" * 70)
        sections.append("")

        # Deep42 Analysis (primary source)
        if deep42_analysis:
            sections.append("Deep42 Market Analysis (Cambrian Network):")
            sections.append(deep42_analysis)
            sections.append("")
        else:
            sections.append("⚠️ Deep42 analysis (Cambrian Network) unavailable")
            sections.append("")

        # Quick Metrics
        sections.append("Quick Metrics (CoinGecko):")

        if cg_metrics:
            mc_change = cg_metrics["market_cap_change_24h"]
            mc_trend = "📈" if mc_change > 0 else "📉"
            sections.append(f"  Market Cap 24h: {mc_change:+.2f}% {mc_trend}")

            btc_dom = cg_metrics["btc_dominance"]
            if btc_dom > 60:
                dom_note = "(High - alts waiting)"
            elif btc_dom > 50:
                dom_note = "(Moderate)"
            else:
                dom_note = "(Low - alt season?)"
            sections.append(f"  BTC Dominance: {btc_dom:.2f}% {dom_note}")
        else:
            sections.append("  ⚠️ CoinGecko metrics unavailable")

        if fg_index:
            value = fg_index["value"]
            classification = fg_index["classification"]

            # Emoji based on value
            if value >= 75:
                emoji = "🔥"
            elif value >= 55:
                emoji = "😊"
            elif value >= 45:
                emoji = "😐"
            elif value >= 25:
                emoji = "😰"
            else:
                emoji = "😱"

            sections.append(f"  Fear & Greed Index (Alternative.me): {value}/100 ({classification}) {emoji}")
        else:
            sections.append("  ⚠️ Fear & Greed Index unavailable")

        sections.append("")
        sections.append("=" * 70)
        sections.append("")

        return "\n".join(sections)

    def get_macro_context(self, force_refresh: bool = False) -> str:
        """
        Get macro context (cached or fresh)

        Args:
            force_refresh: Force refresh even if cache is valid

        Returns:
            Formatted macro context string for LLM prompt
        """
        # Check if refresh needed
        if not force_refresh and not self._should_refresh():
            logger.info(f"Using cached macro context (age: {datetime.now() - self._last_fetch})")
            return self._cached_context

        # Fetch fresh data
        logger.info("Fetching fresh macro context...")

        deep42_analysis = self._fetch_deep42_analysis()
        cg_metrics = self._fetch_coingecko_metrics()
        fg_index = self._fetch_fear_greed_index()

        # Format context
        macro_context = self._format_macro_context(deep42_analysis, cg_metrics, fg_index)

        # Update cache
        self._cached_context = macro_context
        self._last_fetch = datetime.now()

        logger.info("✅ Macro context refreshed")
        return macro_context

    def get_cache_age(self) -> Optional[timedelta]:
        """Get age of cached context"""
        if self._last_fetch is None:
            return None
        return datetime.now() - self._last_fetch
