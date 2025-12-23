"""
Data Aggregator for LLM Funding Arbitrage
==========================================
Fetches and aggregates data from both exchanges:
- Funding rates (with trends)
- Prices and volatility
- Account balances and positions
- Funding clock (time until next payment)
"""

import asyncio
import aiohttp
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple
from collections import deque

logger = logging.getLogger(__name__)

# Constants
FUNDING_PERIODS_PER_YEAR = 1095  # 8h intervals = 3/day * 365
HIBACHI_DATA_API = "https://data-api.hibachi.xyz"
HIBACHI_API = "https://api.hibachi.xyz"


@dataclass
class FundingData:
    """Funding rate data for a single asset on one exchange"""
    symbol: str
    exchange: str
    rate: float  # Current funding rate (per 8h period)
    annualized: float  # Annualized rate %
    next_funding_ts: Optional[int]  # Unix timestamp of next funding
    mark_price: float
    trend: str  # "rising", "falling", "stable"
    rate_history: List[float]  # Recent historical rates


@dataclass
class SpreadData:
    """Spread between two exchanges for an asset"""
    symbol: str
    hibachi_rate: float
    extended_rate: float
    spread: float  # Absolute spread
    annualized_spread: float  # Annualized %
    trend: str  # "widening", "narrowing", "stable"
    short_exchange: str  # Which exchange to SHORT
    long_exchange: str  # Which exchange to LONG
    expected_daily_return: float  # Expected $ per $100 position per day


@dataclass
class VolatilityData:
    """Volatility metrics for an asset"""
    symbol: str
    volatility_1h: float  # 1-hour volatility %
    volatility_24h: float  # 24-hour volatility %
    price_change_1h: float  # % change in last hour
    is_safe: bool  # Whether volatility is within acceptable range


@dataclass
class PositionData:
    """Current position on an exchange"""
    symbol: str
    exchange: str
    side: str  # "LONG" or "SHORT"
    size: float  # Position size in base currency
    notional: float  # USD value
    entry_price: float
    unrealized_pnl: float
    opened_at: Optional[datetime]


@dataclass
class AggregatedData:
    """All data needed for LLM decision"""
    timestamp: datetime

    # Funding data
    funding: Dict[str, Dict[str, FundingData]]  # {symbol: {exchange: FundingData}}
    spreads: Dict[str, SpreadData]  # {symbol: SpreadData}

    # Market data
    volatility: Dict[str, VolatilityData]  # {symbol: VolatilityData}

    # Account data
    hibachi_balance: float
    extended_balance: float
    max_position_size: float  # Calculated from balances

    # Current positions
    positions: List[PositionData]

    # Funding clock
    next_funding_time: Optional[datetime]
    hours_until_funding: Optional[float]


class DataAggregator:
    """
    Aggregates data from Hibachi and Extended for LLM decision making.
    """

    def __init__(self, config):
        self.config = config

        # SDKs will be initialized lazily
        self._hibachi_sdk = None
        self._extended_sdk = None

        # Historical data for trends (keep last 6 data points = ~3 hours at 30min intervals)
        self._funding_history: Dict[str, Dict[str, deque]] = {}
        for symbol in config.symbols:
            self._funding_history[symbol] = {
                "hibachi": deque(maxlen=6),
                "extended": deque(maxlen=6)
            }

        # Price history for volatility
        self._price_history: Dict[str, deque] = {
            symbol: deque(maxlen=60)  # ~1 hour at 1min intervals
            for symbol in config.symbols
        }

    async def initialize(self) -> bool:
        """Initialize exchange connections"""
        try:
            # Import SDKs
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

            from dexes.hibachi.hibachi_sdk import HibachiSDK
            from dexes.extended.extended_sdk import ExtendedSDK

            # Initialize Hibachi
            hibachi_key = os.getenv('HIBACHI_PUBLIC_KEY')
            hibachi_secret = os.getenv('HIBACHI_PRIVATE_KEY')
            hibachi_account = os.getenv('HIBACHI_ACCOUNT_ID')

            if not all([hibachi_key, hibachi_secret, hibachi_account]):
                logger.error("Missing Hibachi credentials in .env")
                return False

            self._hibachi_sdk = HibachiSDK(hibachi_key, hibachi_secret, hibachi_account)
            logger.info("Hibachi SDK initialized")

            # Initialize Extended
            extended_key = os.getenv('EXTENDED_API_KEY')
            extended_stark_private = os.getenv('EXTENDED_STARK_PRIVATE_KEY')
            extended_stark_public = os.getenv('EXTENDED_STARK_PUBLIC_KEY')
            extended_vault = os.getenv('EXTENDED_VAULT')

            if not extended_key:
                logger.error("Missing EXTENDED_API_KEY in .env")
                return False

            self._extended_sdk = ExtendedSDK(
                api_key=extended_key,
                stark_private_key=extended_stark_private,
                stark_public_key=extended_stark_public,
                vault=int(extended_vault) if extended_vault else None
            )
            logger.info("Extended SDK initialized")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize data aggregator: {e}")
            return False

    async def _get_hibachi_funding(self, symbol: str) -> Optional[FundingData]:
        """Fetch funding rate from Hibachi"""
        try:
            hibachi_symbol = self.config.hibachi_symbols.get(symbol)
            if not hibachi_symbol:
                return None

            url = f"{HIBACHI_DATA_API}/market/data/prices?symbol={hibachi_symbol}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"Hibachi funding API error: {response.status}")
                        return None

                    data = await response.json()

                    funding_data = data.get("fundingRateEstimation", {})
                    rate = float(funding_data.get("estimatedFundingRate", 0))
                    next_ts = funding_data.get("nextFundingTimestamp")
                    mark_price = float(data.get("markPrice", 0))

                    # Calculate trend from history
                    history = list(self._funding_history[symbol]["hibachi"])
                    history.append(rate)
                    self._funding_history[symbol]["hibachi"].append(rate)

                    trend = self._calculate_trend(history)

                    return FundingData(
                        symbol=symbol,
                        exchange="Hibachi",
                        rate=rate,
                        annualized=rate * FUNDING_PERIODS_PER_YEAR * 100,
                        next_funding_ts=int(next_ts) if next_ts else None,
                        mark_price=mark_price,
                        trend=trend,
                        rate_history=history[-4:]  # Last 4 data points
                    )

        except Exception as e:
            logger.error(f"Error fetching Hibachi funding for {symbol}: {e}")
            return None

    async def _get_extended_funding(self, symbol: str) -> Optional[FundingData]:
        """Fetch funding rate from Extended"""
        try:
            extended_symbol = self.config.extended_symbols.get(symbol)
            if not extended_symbol:
                return None

            # Use Extended SDK to get market statistics
            if not self._extended_sdk:
                return None

            stats = await self._extended_sdk.get_market_stats(extended_symbol)
            if not stats:
                return None

            rate = float(stats.get('funding_rate', 0))
            mark_price = float(stats.get('mark_price', 0))

            # Calculate trend from history
            history = list(self._funding_history[symbol]["extended"])
            history.append(rate)
            self._funding_history[symbol]["extended"].append(rate)

            trend = self._calculate_trend(history)

            return FundingData(
                symbol=symbol,
                exchange="Extended",
                rate=rate,
                annualized=rate * FUNDING_PERIODS_PER_YEAR * 100,
                next_funding_ts=None,  # Extended doesn't provide this easily
                mark_price=mark_price,
                trend=trend,
                rate_history=history[-4:]
            )

        except Exception as e:
            logger.error(f"Error fetching Extended funding for {symbol}: {e}")
            return None

    def _calculate_trend(self, history: List[float]) -> str:
        """Calculate trend from historical data"""
        if len(history) < 2:
            return "stable"

        # Simple trend: compare latest to average of previous
        if len(history) >= 3:
            prev_avg = sum(history[:-1]) / len(history[:-1])
            current = history[-1]

            change_pct = abs(current - prev_avg) / max(abs(prev_avg), 0.0001) * 100

            if change_pct < 10:
                return "stable"
            elif current > prev_avg:
                return "rising"
            else:
                return "falling"

        return "stable"

    def _calculate_spread(self, hibachi: FundingData, extended: FundingData) -> SpreadData:
        """Calculate spread between two exchanges"""
        spread = hibachi.rate - extended.rate
        annualized = abs(spread) * FUNDING_PERIODS_PER_YEAR * 100

        # Determine which side to take
        if hibachi.rate > extended.rate:
            # Hibachi rate higher -> SHORT Hibachi, LONG Extended
            short_exchange = "Hibachi"
            long_exchange = "Extended"
        else:
            # Extended rate higher -> SHORT Extended, LONG Hibachi
            short_exchange = "Extended"
            long_exchange = "Hibachi"

        # Calculate expected daily return per $100
        # Annualized / 365 = daily, then per $100
        expected_daily = annualized / 365

        # Determine spread trend
        hibachi_trend = hibachi.trend
        extended_trend = extended.trend

        if hibachi_trend == "rising" and extended_trend == "falling":
            spread_trend = "widening"
        elif hibachi_trend == "falling" and extended_trend == "rising":
            spread_trend = "narrowing"
        elif hibachi_trend == extended_trend:
            spread_trend = "stable"
        else:
            spread_trend = "mixed"

        return SpreadData(
            symbol=hibachi.symbol,
            hibachi_rate=hibachi.rate,
            extended_rate=extended.rate,
            spread=abs(spread),
            annualized_spread=annualized,
            trend=spread_trend,
            short_exchange=short_exchange,
            long_exchange=long_exchange,
            expected_daily_return=expected_daily
        )

    async def _get_volatility(self, symbol: str) -> VolatilityData:
        """Calculate volatility for an asset"""
        try:
            # Get recent price from Hibachi (faster API)
            hibachi_symbol = self.config.hibachi_symbols.get(symbol)
            url = f"{HIBACHI_DATA_API}/market/data/prices?symbol={hibachi_symbol}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data.get("markPrice", 0))

                        # Add to history
                        self._price_history[symbol].append({
                            "price": price,
                            "time": datetime.now(timezone.utc)
                        })

            # Calculate volatility from history
            history = list(self._price_history[symbol])

            if len(history) < 2:
                return VolatilityData(
                    symbol=symbol,
                    volatility_1h=0,
                    volatility_24h=0,
                    price_change_1h=0,
                    is_safe=True
                )

            # Get prices from last hour
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            recent_prices = [h["price"] for h in history if h["time"] > one_hour_ago]

            if len(recent_prices) < 2:
                recent_prices = [h["price"] for h in history[-10:]]

            # Calculate volatility (standard deviation / mean)
            if recent_prices:
                mean_price = sum(recent_prices) / len(recent_prices)
                variance = sum((p - mean_price) ** 2 for p in recent_prices) / len(recent_prices)
                volatility_1h = (variance ** 0.5) / mean_price * 100

                # Price change
                price_change_1h = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
            else:
                volatility_1h = 0
                price_change_1h = 0

            # Check if safe
            is_safe = volatility_1h < self.config.max_volatility_1h

            return VolatilityData(
                symbol=symbol,
                volatility_1h=volatility_1h,
                volatility_24h=volatility_1h * 4.9,  # Rough estimate
                price_change_1h=price_change_1h,
                is_safe=is_safe
            )

        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return VolatilityData(
                symbol=symbol,
                volatility_1h=0,
                volatility_24h=0,
                price_change_1h=0,
                is_safe=True
            )

    async def _get_positions(self) -> List[PositionData]:
        """Get current positions from both exchanges"""
        positions = []

        try:
            # Hibachi positions
            if self._hibachi_sdk:
                h_positions = await self._hibachi_sdk.get_positions()
                for p in h_positions:
                    symbol_raw = p.get('symbol', '')
                    # Convert back to normalized symbol
                    symbol = None
                    for s, hs in self.config.hibachi_symbols.items():
                        if hs == symbol_raw:
                            symbol = s
                            break

                    if symbol and float(p.get('quantity', 0)) > 0:
                        positions.append(PositionData(
                            symbol=symbol,
                            exchange="Hibachi",
                            side=p.get('direction', '').upper(),
                            size=float(p.get('quantity', 0)),
                            notional=float(p.get('entryNotional', 0)),
                            entry_price=float(p.get('entryPrice', 0)),
                            unrealized_pnl=float(p.get('unrealizedPnl', 0)),
                            opened_at=None  # Would need to track this
                        ))

            # Extended positions
            if self._extended_sdk:
                e_positions = await self._extended_sdk.get_positions()
                if e_positions:
                    for p in e_positions:
                        market = p.get('market', '')
                        symbol = None
                        for s, es in self.config.extended_symbols.items():
                            if es == market:
                                symbol = s
                                break

                        if symbol and float(p.get('size', 0)) > 0:
                            positions.append(PositionData(
                                symbol=symbol,
                                exchange="Extended",
                                side=p.get('side', '').upper(),
                                size=float(p.get('size', 0)),
                                notional=float(p.get('value', 0)),
                                entry_price=float(p.get('openPrice', 0)),
                                unrealized_pnl=float(p.get('unrealisedPnl', 0)),
                                opened_at=None
                            ))

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")

        return positions

    async def _get_balances(self) -> Tuple[float, float]:
        """Get balances from both exchanges"""
        hibachi_balance = 0.0
        extended_balance = 0.0

        try:
            if self._hibachi_sdk:
                bal = await self._hibachi_sdk.get_balance()
                if bal:
                    hibachi_balance = float(bal)

            if self._extended_sdk:
                bal = await self._extended_sdk.get_balance()
                if isinstance(bal, dict):
                    extended_balance = float(bal.get('equity', 0))
                elif bal:
                    extended_balance = float(bal)

        except Exception as e:
            logger.error(f"Error fetching balances: {e}")

        return hibachi_balance, extended_balance

    async def aggregate(self) -> Optional[AggregatedData]:
        """
        Aggregate all data needed for LLM decision.
        Returns None if critical data is missing.
        """
        try:
            logger.info("Aggregating data from both exchanges...")

            # Fetch all data concurrently
            funding_tasks = []
            for symbol in self.config.symbols:
                funding_tasks.append(self._get_hibachi_funding(symbol))
                funding_tasks.append(self._get_extended_funding(symbol))

            volatility_tasks = [self._get_volatility(s) for s in self.config.symbols]

            # Run all fetches concurrently
            funding_results = await asyncio.gather(*funding_tasks, return_exceptions=True)
            volatility_results = await asyncio.gather(*volatility_tasks, return_exceptions=True)
            positions = await self._get_positions()
            hibachi_balance, extended_balance = await self._get_balances()

            # Organize funding data
            funding: Dict[str, Dict[str, FundingData]] = {}
            spreads: Dict[str, SpreadData] = {}

            for i, symbol in enumerate(self.config.symbols):
                hibachi_funding = funding_results[i * 2]
                extended_funding = funding_results[i * 2 + 1]

                if isinstance(hibachi_funding, Exception) or isinstance(extended_funding, Exception):
                    logger.warning(f"Failed to get funding for {symbol}")
                    continue

                if hibachi_funding and extended_funding:
                    funding[symbol] = {
                        "Hibachi": hibachi_funding,
                        "Extended": extended_funding
                    }
                    spreads[symbol] = self._calculate_spread(hibachi_funding, extended_funding)

            # Check if we have funding data (CRITICAL)
            if not funding:
                logger.error("CRITICAL: No funding rate data available!")
                return None

            # Organize volatility data
            volatility: Dict[str, VolatilityData] = {}
            for i, symbol in enumerate(self.config.symbols):
                vol = volatility_results[i]
                if not isinstance(vol, Exception):
                    volatility[symbol] = vol

            # Calculate max position size
            min_balance = min(hibachi_balance, extended_balance)
            max_position = min(
                min_balance * self.config.max_position_pct,
                self.config.max_position_usd
            )

            # Get next funding time (from any Hibachi funding data)
            next_funding_time = None
            hours_until_funding = None
            for symbol_data in funding.values():
                hibachi_data = symbol_data.get("Hibachi")
                if hibachi_data and hibachi_data.next_funding_ts:
                    next_funding_time = datetime.fromtimestamp(
                        hibachi_data.next_funding_ts / 1000,  # ms to s
                        tz=timezone.utc
                    )
                    hours_until_funding = (next_funding_time - datetime.now(timezone.utc)).total_seconds() / 3600
                    break

            return AggregatedData(
                timestamp=datetime.now(timezone.utc),
                funding=funding,
                spreads=spreads,
                volatility=volatility,
                hibachi_balance=hibachi_balance,
                extended_balance=extended_balance,
                max_position_size=max_position,
                positions=positions,
                next_funding_time=next_funding_time,
                hours_until_funding=hours_until_funding
            )

        except Exception as e:
            logger.error(f"Error aggregating data: {e}")
            return None
