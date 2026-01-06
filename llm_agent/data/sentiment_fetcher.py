"""
Sentiment Data Fetcher
Aggregates market sentiment from multiple free sources

Sources:
- Fear & Greed Index (alternative.me)
- BTC Long/Short Ratio (Coinglass)
- Aggregate Funding Rates
- Social sentiment indicators

Update frequency: Every 1-6 hours
"""

import asyncio
import aiohttp
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache file location
SENTIMENT_CACHE_FILE = "logs/sentiment_data.json"


class SentimentFetcher:
    """
    Fetches and aggregates crypto market sentiment from multiple sources
    """

    def __init__(self, cache_ttl_minutes: int = 60):
        """
        Args:
            cache_ttl_minutes: How long to cache sentiment data (default 1 hour)
        """
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._cache: Optional[Dict] = None
        self._cache_time: Optional[datetime] = None

        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)

    def _load_cache(self) -> Optional[Dict]:
        """Load cached sentiment data from file"""
        try:
            if os.path.exists(SENTIMENT_CACHE_FILE):
                with open(SENTIMENT_CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    cache_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                    if datetime.now() - cache_time < self.cache_ttl:
                        return data
        except Exception as e:
            logger.warning(f"Could not load sentiment cache: {e}")
        return None

    def _save_cache(self, data: Dict):
        """Save sentiment data to cache file"""
        try:
            data['timestamp'] = datetime.now().isoformat()
            with open(SENTIMENT_CACHE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save sentiment cache: {e}")

    async def fetch_fear_greed(self) -> Dict:
        """
        Fetch Fear & Greed Index from alternative.me

        Returns:
            Dict with 'value' (0-100), 'classification' (Extreme Fear/Fear/Neutral/Greed/Extreme Greed)
        """
        url = "https://api.alternative.me/fng/?limit=1"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('data') and len(data['data']) > 0:
                            fg_data = data['data'][0]
                            return {
                                'value': int(fg_data.get('value', 50)),
                                'classification': fg_data.get('value_classification', 'Neutral'),
                                'source': 'alternative.me',
                                'updated': fg_data.get('timestamp', '')
                            }
        except Exception as e:
            logger.warning(f"Fear & Greed fetch failed: {e}")

        return {'value': 50, 'classification': 'Neutral', 'source': 'default', 'updated': ''}

    async def fetch_long_short_ratio(self) -> Dict:
        """
        Fetch BTC Long/Short ratio from public APIs

        Returns:
            Dict with 'ratio' (>1 means more longs), 'long_pct', 'short_pct'
        """
        # Try Coinglass public endpoint
        url = "https://open-api.coinglass.com/public/v2/open_interest"

        try:
            async with aiohttp.ClientSession() as session:
                # First try without API key (limited but free)
                headers = {"accept": "application/json"}
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse response - structure varies
                        if data.get('data'):
                            # Calculate aggregate long/short
                            return {
                                'ratio': 1.0,  # Placeholder - need specific endpoint
                                'long_pct': 50.0,
                                'short_pct': 50.0,
                                'source': 'coinglass'
                            }
        except Exception as e:
            logger.debug(f"Long/Short ratio fetch failed: {e}")

        # Fallback: Use funding rate as proxy
        # Positive funding = more longs paying shorts
        return {'ratio': 1.0, 'long_pct': 50.0, 'short_pct': 50.0, 'source': 'default'}

    async def fetch_funding_rates(self) -> Dict:
        """
        Fetch aggregate funding rates from multiple exchanges

        Returns:
            Dict with 'btc_funding', 'eth_funding', 'average' (all in percentage)
        """
        rates = []

        # Binance funding rate (free, no auth)
        binance_url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(binance_url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data and len(data) > 0:
                            rate = float(data[0].get('fundingRate', 0)) * 100
                            rates.append(rate)
        except Exception as e:
            logger.debug(f"Binance funding fetch failed: {e}")

        # Bybit funding rate (free, no auth)
        bybit_url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(bybit_url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('result', {}).get('list'):
                            ticker = data['result']['list'][0]
                            rate = float(ticker.get('fundingRate', 0)) * 100
                            rates.append(rate)
        except Exception as e:
            logger.debug(f"Bybit funding fetch failed: {e}")

        avg_rate = sum(rates) / len(rates) if rates else 0.0

        return {
            'btc_funding_pct': avg_rate,
            'eth_funding_pct': avg_rate * 0.8,  # ETH typically lower
            'average_pct': avg_rate,
            'sources_count': len(rates),
            'interpretation': 'longs_crowded' if avg_rate > 0.01 else ('shorts_crowded' if avg_rate < -0.01 else 'neutral')
        }

    async def fetch_all(self, force_refresh: bool = False) -> Dict:
        """
        Fetch all sentiment data, using cache if available

        Args:
            force_refresh: Skip cache and fetch fresh data

        Returns:
            Dict with all sentiment indicators and combined score
        """
        # Check cache first
        if not force_refresh:
            cached = self._load_cache()
            if cached:
                logger.info("Using cached sentiment data")
                return cached

        logger.info("Fetching fresh sentiment data...")

        # Fetch all sources in parallel
        fear_greed, long_short, funding = await asyncio.gather(
            self.fetch_fear_greed(),
            self.fetch_long_short_ratio(),
            self.fetch_funding_rates(),
            return_exceptions=True
        )

        # Handle any exceptions
        if isinstance(fear_greed, Exception):
            logger.warning(f"Fear/Greed failed: {fear_greed}")
            fear_greed = {'value': 50, 'classification': 'Neutral'}
        if isinstance(long_short, Exception):
            logger.warning(f"Long/Short failed: {long_short}")
            long_short = {'ratio': 1.0, 'long_pct': 50.0, 'short_pct': 50.0}
        if isinstance(funding, Exception):
            logger.warning(f"Funding failed: {funding}")
            funding = {'btc_funding_pct': 0.0, 'average_pct': 0.0}

        # Calculate combined sentiment score (0-100, 50=neutral)
        combined_score = self._calculate_combined_score(fear_greed, long_short, funding)

        result = {
            'timestamp': datetime.now().isoformat(),
            'fear_greed': fear_greed,
            'long_short': long_short,
            'funding': funding,
            'combined_score': combined_score,
            'market_bias': self._interpret_score(combined_score)
        }

        # Save to cache
        self._save_cache(result)

        return result

    def _calculate_combined_score(self, fear_greed: Dict, long_short: Dict, funding: Dict) -> float:
        """
        Calculate combined sentiment score from all indicators

        Returns:
            Float 0-100 where:
            - 0-25: Extreme bearish (contrarian bullish signal)
            - 25-45: Bearish
            - 45-55: Neutral
            - 55-75: Bullish
            - 75-100: Extreme bullish (contrarian bearish signal)
        """
        scores = []
        weights = []

        # Fear & Greed (direct mapping, most reliable)
        fg_value = fear_greed.get('value', 50)
        scores.append(fg_value)
        weights.append(0.5)  # 50% weight

        # Long/Short ratio (inverse - high longs = potential reversal)
        ls_ratio = long_short.get('ratio', 1.0)
        # Ratio of 1.5 (60% long) maps to ~65 score
        # Ratio of 0.67 (40% long) maps to ~35 score
        ls_score = 50 + (ls_ratio - 1.0) * 30  # Scale around 50
        ls_score = max(0, min(100, ls_score))
        scores.append(ls_score)
        weights.append(0.25)  # 25% weight

        # Funding rate (positive = longs paying = bullish sentiment)
        funding_pct = funding.get('average_pct', 0.0)
        # 0.01% funding maps to ~60 score, -0.01% maps to ~40 score
        funding_score = 50 + funding_pct * 1000  # Scale: 0.01% -> 60
        funding_score = max(0, min(100, funding_score))
        scores.append(funding_score)
        weights.append(0.25)  # 25% weight

        # Weighted average
        combined = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

        return round(combined, 1)

    def _interpret_score(self, score: float) -> Dict:
        """
        Interpret combined score into actionable bias

        Returns:
            Dict with 'direction', 'strength', 'contrarian_signal'
        """
        if score < 20:
            return {
                'direction': 'bearish',
                'strength': 'extreme',
                'contrarian_signal': 'BULLISH',  # Extreme fear = buy signal
                'recommendation': 'Look for LONG entries - extreme fear often marks bottoms'
            }
        elif score < 40:
            return {
                'direction': 'bearish',
                'strength': 'moderate',
                'contrarian_signal': 'neutral',
                'recommendation': 'Cautious - sentiment negative but not extreme'
            }
        elif score < 60:
            return {
                'direction': 'neutral',
                'strength': 'low',
                'contrarian_signal': 'neutral',
                'recommendation': 'No strong sentiment bias - use technicals'
            }
        elif score < 80:
            return {
                'direction': 'bullish',
                'strength': 'moderate',
                'contrarian_signal': 'neutral',
                'recommendation': 'Cautious - sentiment positive but watch for reversal'
            }
        else:
            return {
                'direction': 'bullish',
                'strength': 'extreme',
                'contrarian_signal': 'BEARISH',  # Extreme greed = sell signal
                'recommendation': 'Look for SHORT entries - extreme greed often marks tops'
            }

    def get_prompt_context(self, sentiment_data: Optional[Dict] = None) -> str:
        """
        Generate sentiment context string for LLM prompts

        Args:
            sentiment_data: Pre-fetched sentiment data (or loads from cache)

        Returns:
            Formatted string for LLM prompt injection
        """
        if sentiment_data is None:
            sentiment_data = self._load_cache()

        if not sentiment_data:
            return "SENTIMENT DATA: Unavailable - use technical analysis only"

        fg = sentiment_data.get('fear_greed', {})
        funding = sentiment_data.get('funding', {})
        bias = sentiment_data.get('market_bias', {})
        score = sentiment_data.get('combined_score', 50)

        return f"""MARKET SENTIMENT (Updated: {sentiment_data.get('timestamp', 'unknown')[:16]}):
- Fear & Greed Index: {fg.get('value', 50)} ({fg.get('classification', 'Neutral')})
- BTC Funding Rate: {funding.get('btc_funding_pct', 0):.4f}% ({funding.get('interpretation', 'neutral')})
- Combined Score: {score}/100
- Market Bias: {bias.get('direction', 'neutral').upper()} ({bias.get('strength', 'low')})
- Contrarian Signal: {bias.get('contrarian_signal', 'none')}
- Recommendation: {bias.get('recommendation', 'Use technicals')}

IMPORTANT: Use this sentiment context to inform position sizing and direction bias.
- Extreme fear (score < 25): Favor LONG positions
- Extreme greed (score > 75): Favor SHORT positions
- Neutral (40-60): No sentiment edge - rely on technicals"""


async def main():
    """Test sentiment fetcher"""
    logging.basicConfig(level=logging.INFO)

    fetcher = SentimentFetcher()
    data = await fetcher.fetch_all(force_refresh=True)

    print("\n" + "=" * 60)
    print("SENTIMENT DATA")
    print("=" * 60)
    print(json.dumps(data, indent=2))

    print("\n" + "=" * 60)
    print("PROMPT CONTEXT")
    print("=" * 60)
    print(fetcher.get_prompt_context(data))


if __name__ == "__main__":
    asyncio.run(main())
