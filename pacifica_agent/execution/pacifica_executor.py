"""
Pacifica Trade Executor
Executes LLM trading decisions using Pacifica SDK

Mirrors Pacifica TradeExecutor structure but adapted for Pacifica DEX
"""

import logging
import sys
import os
import asyncio
import requests
from typing import Optional, Dict
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trade_tracker import TradeTracker
from pacifica_agent.data.liquidity_checker import LiquidityChecker

logger = logging.getLogger(__name__)


class PacificaTradeExecutor:
    """
    Execute LLM trading decisions for Pacifica DEX

    Args:
        pacifica_sdk: PacificaSDK instance for order placement
        trade_tracker: TradeTracker instance for logging
        dry_run: If True, don't actually place orders (default: False)
        default_position_size: Default position size in USD (default: $5 for $100 account)
        max_positions: Max open positions (default: 3)
    """

    # NO HARDCODED MAPPINGS - All market data fetched dynamically from SDK

    def __init__(
        self,
        pacifica_sdk,  # PacificaSDK instance
        trade_tracker: TradeTracker,
        dry_run: bool = False,
        default_position_size: float = 250.0,  # $250 notional = $5 margin @ 50x leverage
        max_positions: int = 15,
        cambrian_api_key: str = None,  # For Deep42 sentiment filtering
        sentiment_threshold_bullish: float = 60.0,  # Min bullish % for longs (60%)
        sentiment_threshold_bearish: float = 40.0,  # Min bearish % for shorts (40%)
        use_sentiment_filter: bool = False,  # Enable/disable sentiment filtering
        max_position_age_minutes: int = 60  # Maximum position age before auto-close (default: 60 min)
    ):
        self.sdk = pacifica_sdk
        self.tracker = trade_tracker
        self.dry_run = dry_run
        self.default_position_size = default_position_size
        self.max_positions = max_positions
        self.liquidity_checker = LiquidityChecker(pacifica_sdk)

        # Deep42 sentiment filtering
        self.cambrian_api_key = cambrian_api_key
        self.sentiment_threshold_bullish = sentiment_threshold_bullish
        self.sentiment_threshold_bearish = sentiment_threshold_bearish
        self.use_sentiment_filter = use_sentiment_filter and cambrian_api_key is not None

        # Position aging/rotation (REQ-1.5)
        self.max_position_age_minutes = max_position_age_minutes

        mode = "DRY-RUN" if dry_run else "LIVE"
        sentiment_mode = f", Sentiment Filter: {'ON' if self.use_sentiment_filter else 'OFF'}"
        aging_mode = f", Max Age: {max_position_age_minutes}min"
        logger.info(f"✅ PacificaTradeExecutor initialized ({mode} mode, ${default_position_size}/trade{sentiment_mode}{aging_mode})")

    async def _fetch_account_balance(self) -> Optional[float]:
        """Fetch account balance from Pacifica API"""
        try:
            # Run sync SDK call in thread pool to avoid blocking event loop
            import asyncio
            balance_result = await asyncio.to_thread(self.sdk.get_balance)

            # Check if API call succeeded
            if not balance_result.get('success'):
                status_code = balance_result.get('status_code', 'unknown')
                error_text = balance_result.get('text', 'No error message')[:100]
                logger.warning(f"❌ Balance API failed (HTTP {status_code}): {error_text}")
                return None

            # Extract balance data
            data = balance_result.get('data')
            if not data:
                logger.warning(f"❌ Balance API returned no data: {balance_result}")
                return None

            # Try multiple balance fields (different API versions)
            account_equity = (
                data.get('account_equity') or
                data.get('available_to_spend') or
                data.get('balance') or
                0
            )

            account_equity = float(account_equity)

            if account_equity <= 0:
                logger.warning(f"❌ Invalid balance: ${account_equity:.2f}")
                return None

            logger.debug(f"✅ Account equity: ${account_equity:.2f}")
            return account_equity

        except Exception as e:
            logger.warning(f"❌ Error fetching balance: {e}")
            logger.debug(f"Exception details: {type(e).__name__}: {str(e)}")
            return None

    async def _fetch_open_positions(self):
        """Fetch current open positions from Pacifica API"""
        try:
            # Note: SDK method is synchronous (uses requests.get, not async)
            result = self.sdk.get_positions()
            if result.get("success") and result.get("data"):
                return result["data"]
            return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    def _check_sentiment_alignment(self, symbol: str, action: str) -> tuple[bool, str]:
        """
        Check if social sentiment aligns with trading action using Deep42

        Args:
            symbol: Token symbol (e.g., 'SOL', 'BTC')
            action: Trading action ('BUY' or 'SELL')

        Returns:
            (should_proceed: bool, reason: str)
        """
        # Skip if sentiment filter disabled
        if not self.use_sentiment_filter:
            return (True, "Sentiment filter disabled")

        try:
            # Query Deep42 token sentiment (24h window)
            url = "https://deep42.cambrian.network/api/v1/deep42/social-data/token-analysis"
            params = {
                "symbol": symbol,
                "days": 1,
                "granularity": "total"
            }
            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Deep42 API error for {symbol}: HTTP {response.status_code}")
                return (True, f"Sentiment API unavailable (HTTP {response.status_code}), proceeding anyway")

            data = response.json()

            # Extract sentiment metrics
            bullish_pct = data.get('veryBullishPct', 0) + data.get('bullishPct', 0)
            bearish_pct = data.get('bearishPct', 0)
            avg_sentiment = data.get('avgSentiment', 5.0)
            total_tweets = data.get('totalTweets', 0)

            # Check alignment based on action
            if action == "BUY":
                # For longs, require bullish sentiment
                if bullish_pct < self.sentiment_threshold_bullish:
                    reason = f"❌ Sentiment too weak for LONG: {bullish_pct:.1f}% bullish (need ≥{self.sentiment_threshold_bullish}%), sentiment {avg_sentiment:.1f}/10"
                    logger.info(f"{symbol} {reason}")
                    return (False, reason)
                else:
                    reason = f"✅ Sentiment aligned for LONG: {bullish_pct:.1f}% bullish, sentiment {avg_sentiment:.1f}/10, {total_tweets} tweets"
                    logger.info(f"{symbol} {reason}")
                    return (True, reason)

            elif action == "SELL":
                # For shorts, require bearish sentiment OR weak bullish
                if bullish_pct > (100 - self.sentiment_threshold_bearish):
                    reason = f"❌ Sentiment too bullish for SHORT: {bullish_pct:.1f}% bullish (need <{100 - self.sentiment_threshold_bearish}%), sentiment {avg_sentiment:.1f}/10"
                    logger.info(f"{symbol} {reason}")
                    return (False, reason)
                else:
                    reason = f"✅ Sentiment aligned for SHORT: {bullish_pct:.1f}% bullish, {bearish_pct:.1f}% bearish, sentiment {avg_sentiment:.1f}/10"
                    logger.info(f"{symbol} {reason}")
                    return (True, reason)

            return (True, "Unknown action, allowing")

        except Exception as e:
            logger.warning(f"Sentiment check failed for {symbol}: {e}")
            return (True, f"Sentiment check failed ({str(e)}), proceeding anyway")

    def _check_sentiment_shifts(self, symbol: str) -> Optional[Dict]:
        """
        Check for major sentiment shifts that signal trend reversals

        Args:
            symbol: Token symbol (e.g., 'SOL', 'BTC')

        Returns:
            Dict with shift info if major shift detected, None otherwise
            {
                'symbol': str,
                'shift_direction': 'positive' | 'negative',
                'sentiment_shift': float,  # Magnitude of shift (-10 to +10)
                'current_sentiment': float,  # Current sentiment (0-10)
                'previous_sentiment': float,  # Previous sentiment (0-10)
                'timeframe': str  # '1h', '4h', or '24h'
            }
        """
        # Skip if sentiment filter disabled (sentiment shifts require API key)
        if not self.use_sentiment_filter:
            return None

        try:
            # Query Deep42 sentiment shifts
            url = "https://deep42.cambrian.network/api/v1/deep42/social-data/sentiment-shifts"
            params = {
                "token": symbol,  # Filter for specific token
                "threshold": 1.5,  # Minimum shift magnitude to detect
                "period": "4h"  # Check 4-hour shifts (good balance)
            }
            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.debug(f"Sentiment shifts API unavailable for {symbol}: HTTP {response.status_code}")
                return None

            shifts_data = response.json()

            # Check if any shifts detected for this symbol
            if not shifts_data or len(shifts_data) == 0:
                logger.debug(f"No major sentiment shifts detected for {symbol}")
                return None

            # Get the most recent/significant shift
            shift = shifts_data[0] if isinstance(shifts_data, list) else shifts_data

            shift_magnitude = shift.get('sentiment_shift', 0)
            shift_direction = shift.get('shift_direction', 'neutral')
            current_sentiment = shift.get('current_sentiment', 5.0)
            previous_sentiment = shift.get('previous_sentiment', 5.0)
            timeframe = shift.get('timeframe', '4h')

            # Log detected shift
            if abs(shift_magnitude) >= 2.0:
                # Major shift (>2.0 points)
                direction_emoji = "🚀" if shift_direction == 'positive' else "📉"
                logger.warning(
                    f"{direction_emoji} MAJOR sentiment shift detected for {symbol}: "
                    f"{shift_direction.upper()} {abs(shift_magnitude):.1f} points "
                    f"({previous_sentiment:.1f} → {current_sentiment:.1f}) in {timeframe}"
                )
            else:
                # Moderate shift (1.5-2.0 points)
                logger.info(
                    f"📊 Sentiment shift for {symbol}: {shift_direction} "
                    f"{abs(shift_magnitude):.1f} points ({timeframe})"
                )

            return {
                'symbol': symbol,
                'shift_direction': shift_direction,
                'sentiment_shift': shift_magnitude,
                'current_sentiment': current_sentiment,
                'previous_sentiment': previous_sentiment,
                'timeframe': timeframe
            }

        except Exception as e:
            logger.debug(f"Sentiment shifts check failed for {symbol}: {e}")
            return None

    def _check_alpha_tweets(self, symbol: str) -> Optional[Dict]:
        """
        Check for high-quality alpha signals from Twitter using Deep42

        Args:
            symbol: Token symbol (e.g., 'SOL', 'BTC')

        Returns:
            Dict with alpha info if exceptional alpha found, None otherwise
            {
                'symbol': str,
                'alpha_count': int,  # Number of alpha tweets found
                'max_score': float,  # Highest combined score
                'avg_score': float,  # Average combined score
                'position_multiplier': float  # 1.0 to 2.0 (position size boost)
            }
        """
        # Skip if sentiment filter disabled (alpha detection requires API key)
        if not self.use_sentiment_filter:
            return None

        try:
            # Query Deep42 alpha tweet detection
            url = "https://deep42.cambrian.network/api/v1/deep42/social-data/alpha-tweet-detection"
            params = {
                "token_filter": symbol,
                "min_threshold": 20,  # Minimum quality threshold (20-30 range)
                "limit": 10  # Check last 10 tweets
            }
            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                logger.debug(f"Alpha tweets API unavailable for {symbol}: HTTP {response.status_code}")
                return None

            alpha_tweets = response.json()

            # Check if any alpha found
            if not alpha_tweets or len(alpha_tweets) == 0:
                logger.debug(f"No alpha tweets found for {symbol}")
                return None

            # Calculate alpha metrics
            scores = [tweet.get('combined_score', 0) for tweet in alpha_tweets]
            max_score = max(scores) if scores else 0
            avg_score = sum(scores) / len(scores) if scores else 0
            alpha_count = len(alpha_tweets)

            # Count exceptional alpha (>30 score)
            exceptional_count = len([s for s in scores if s > 30])

            # Determine position size multiplier based on alpha quality
            if exceptional_count >= 2:
                # Multiple exceptional alpha signals
                multiplier = 2.0
                logger.warning(
                    f"💎 EXCEPTIONAL ALPHA for {symbol}: "
                    f"{exceptional_count} tweets >30 score (max: {max_score:.1f})"
                )
            elif max_score >= 30:
                # Single exceptional alpha
                multiplier = 1.5
                logger.info(
                    f"✨ HIGH QUALITY ALPHA for {symbol}: "
                    f"Max score {max_score:.1f} (avg: {avg_score:.1f})"
                )
            elif max_score >= 25:
                # Good alpha
                multiplier = 1.2
                logger.info(
                    f"📊 GOOD ALPHA for {symbol}: "
                    f"Max score {max_score:.1f} (avg: {avg_score:.1f})"
                )
            else:
                # Moderate alpha - no boost
                multiplier = 1.0
                logger.debug(f"Alpha tweets for {symbol}: max {max_score:.1f}")

            return {
                'symbol': symbol,
                'alpha_count': alpha_count,
                'max_score': max_score,
                'avg_score': avg_score,
                'position_multiplier': multiplier
            }

        except Exception as e:
            logger.debug(f"Alpha tweets check failed for {symbol}: {e}")
            return None

    async def check_stale_positions(self):
        """
        Check for stale positions and close them to free up capital

        REQ-1.5: Position aging/rotation
        Based on Lighter bot Nov 7 success - quick exits on winners

        Returns:
            List of closed position symbols
        """
        closed_symbols = []

        # Get open positions from tracker
        open_trades = self.tracker.get_open_trades()

        if not open_trades:
            logger.debug("No open positions to check for aging")
            return closed_symbols

        now = datetime.now()
        # Ensure threshold is int (defensive programming)
        age_threshold_minutes = int(self.max_position_age_minutes) if self.max_position_age_minutes else 60

        logger.info(f"🕐 Checking {len(open_trades)} positions for staleness (max age: {age_threshold_minutes} min)")

        for trade in open_trades:
            symbol = trade.get('symbol')
            timestamp_str = trade.get('timestamp')

            if not timestamp_str:
                logger.warning(f"Position {symbol} has no timestamp - skipping age check")
                continue

            try:
                # Parse timestamp
                entry_time = datetime.fromisoformat(timestamp_str)
                age_minutes = (now - entry_time).total_seconds() / 60

                # Check if position is stale
                if age_minutes > age_threshold_minutes:
                    logger.warning(
                        f"⏰ STALE POSITION: {symbol} open for {age_minutes:.1f} min "
                        f"(threshold: {age_threshold_minutes} min) - auto-closing"
                    )

                    # Close position
                    close_result = await self._close_position(
                        symbol=symbol,
                        reason=f"Position aging: open for {age_minutes:.1f} min (max: {age_threshold_minutes} min)"
                    )

                    if close_result.get('success'):
                        logger.info(f"✅ Closed stale position {symbol}")
                        closed_symbols.append(symbol)
                    else:
                        logger.error(f"❌ Failed to close stale position {symbol}: {close_result.get('error')}")
                else:
                    logger.debug(f"Position {symbol} age: {age_minutes:.1f} min (OK)")

            except Exception as e:
                logger.error(f"Error checking position age for {symbol}: {e}")
                continue

        if closed_symbols:
            logger.info(f"🔄 Rotation complete: Closed {len(closed_symbols)} stale positions: {', '.join(closed_symbols)}")
        else:
            logger.debug("No stale positions found")

        return closed_symbols

    async def execute_decision(self, decision: Dict) -> Dict:
        """
        Execute LLM trading decision (async for Pacifica)

        Args:
            decision: Dict with keys: action, symbol, reason, confidence

        Returns:
            Dict with execution result
        """
        action = decision.get("action")
        symbol = decision.get("symbol")
        reason = decision.get("reason", "")

        logger.info(f"Executing decision: {action} {symbol or ''}")
        reason_condensed = reason.replace('\n', ' ').strip()
        logger.info(f"Reason: {reason_condensed}")

        # Handle NOTHING
        if action == "NOTHING":
            logger.info("No action to execute")
            return {
                "success": True,
                "action": "NOTHING",
                "symbol": None,
                "order_id": None,
                "filled_size": None,
                "filled_price": None,
                "error": None
            }

        # Handle CLOSE
        if action == "CLOSE":
            return await self._close_position(symbol, reason)

        # Handle BUY/SELL
        if action in ["BUY", "SELL"]:
            return await self._open_position(action, symbol, reason, decision)

        # Invalid action
        logger.error(f"Invalid action: {action}")
        return {
            "success": False,
            "action": action,
            "symbol": symbol,
            "order_id": None,
            "filled_size": None,
            "filled_price": None,
            "error": f"Invalid action: {action}"
        }

    async def _open_position(self, action: str, symbol: str, reason: str, decision: Dict = None) -> Dict:
        """
        Open new position (BUY=LONG, SELL=SHORT)

        Args:
            action: BUY or SELL
            symbol: Market symbol
            reason: LLM reasoning
            decision: Full decision dict with confidence

        Returns:
            Execution result dict
        """
        side = "LONG" if action == "BUY" else "SHORT"
        sdk_side = "bid" if action == "BUY" else "ask"

        logger.info(f"Opening {side} position in {symbol}")

        # 🔍 SENTIMENT FILTER - Check Deep42 social sentiment alignment
        should_proceed, sentiment_reason = self._check_sentiment_alignment(symbol, action)
        if not should_proceed:
            logger.warning(f"🚫 Trade rejected by sentiment filter: {symbol} {action}")
            return {
                "success": False,
                "action": action,
                "symbol": symbol,
                "error": f"Sentiment filter: {sentiment_reason}",
                "skipped_reason": "sentiment_mismatch"
            }

        # 🔍 SENTIMENT SHIFTS - Check for major trend reversals
        sentiment_shift = self._check_sentiment_shifts(symbol)
        if sentiment_shift:
            shift_dir = sentiment_shift['shift_direction']
            shift_mag = sentiment_shift['sentiment_shift']

            # Reject trades against major negative shifts
            if action == "BUY" and shift_dir == 'negative' and abs(shift_mag) >= 2.0:
                logger.warning(
                    f"🚫 Trade rejected by sentiment shift: {symbol} {action} - "
                    f"Major bearish shift detected ({abs(shift_mag):.1f} points)"
                )
                return {
                    "success": False,
                    "action": action,
                    "symbol": symbol,
                    "error": f"Major bearish sentiment shift detected ({abs(shift_mag):.1f} points)",
                    "skipped_reason": "sentiment_reversal"
                }

            elif action == "SELL" and shift_dir == 'positive' and abs(shift_mag) >= 2.0:
                logger.warning(
                    f"🚫 Trade rejected by sentiment shift: {symbol} {action} - "
                    f"Major bullish shift detected ({abs(shift_mag):.1f} points)"
                )
                return {
                    "success": False,
                    "action": action,
                    "symbol": symbol,
                    "error": f"Major bullish sentiment shift detected ({abs(shift_mag):.1f} points)",
                    "skipped_reason": "sentiment_reversal"
                }

        # Check max positions - count ALL positions on exchange
        open_positions = await self._fetch_open_positions()
        if len(open_positions) >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached (exchange has {len(open_positions)} positions)")
            return {
                "success": False,
                "action": action,
                "symbol": symbol,
                "error": f"Max positions ({self.max_positions}) reached"
            }

        # Note: Pacifica SDK accepts symbol directly, no need for market_id lookup

        # Get current price (approximate - Pacifica uses market orders)
        # For scalping strategy, use small fixed position sizes
        confidence = decision.get("confidence", 0.5)

        # Get account balance for dynamic sizing
        account_balance = await self._fetch_account_balance()

        # LEVERAGE-AWARE POSITION SIZING (Margin-Based)
        # Think in terms of MARGIN USAGE (% of account), not notional value
        # With perps, we can use 5-10x leverage to amplify position size
        if account_balance and account_balance > 1.0:
            # Pacifica uses 50x leverage (confirmed from UI)
            # With 50x: $250 notional = $5 margin (matches Lighter's margin usage)
            assumed_leverage = 50.0

            # Reserve percentage (10% held back for safety)
            reserve_pct = 0.10
            available_margin = account_balance * (1 - reserve_pct)

            # Confidence-based MARGIN USAGE per trade (% of available margin)
            # High confidence = use more margin = bigger position
            if confidence < 0.5:
                margin_pct = 0.08  # 8% margin usage (conservative)
            elif confidence < 0.7:
                margin_pct = 0.12  # 12% margin usage
            elif confidence < 0.85:
                margin_pct = 0.18  # 18% margin usage (aggressive)
            else:
                margin_pct = 0.25  # 25% margin usage (very aggressive on high confidence)

            # Calculate margin to use for this trade
            margin_to_use = available_margin * margin_pct

            # Notional position = margin * leverage
            calculated_size = margin_to_use * assumed_leverage

            # 🔍 ALPHA BOOST - Check for exceptional alpha and boost position size
            alpha_info = self._check_alpha_tweets(symbol)
            if alpha_info and alpha_info['position_multiplier'] > 1.0:
                original_size = calculated_size
                calculated_size *= alpha_info['position_multiplier']
                logger.info(
                    f"🚀 ALPHA BOOST: {symbol} position size "
                    f"${original_size:.2f} → ${calculated_size:.2f} "
                    f"({alpha_info['position_multiplier']:.1f}x multiplier, "
                    f"max alpha score: {alpha_info['max_score']:.1f})"
                )

            # Default exchange minimums (used as fallback if no metadata available)
            # Most Pacifica markets have $10 minimum
            default_min_config = {'base_units': 0.01, 'usd': 10.0}

            # Try to get minimums from SDK metadata if available
            # For now use default - could be enhanced to fetch from API in future
            min_config = default_min_config

            # Get current price to calculate minimum in USD
            # Try to get from decision first (passed from bot), otherwise use estimates
            current_price = decision.get('current_price')
            if not current_price:
                price_estimates = {
                    'BTC': 101500.0,  # Updated estimate
                    'SOL': 155.0,
                    'ETH': 3400.0,
                    'PENGU': 0.014,
                    'XPL': 0.92,
                    'ASTER': 2.11,
                }
                current_price = price_estimates.get(symbol, 100.0)
                logger.warning(f"⚠️  Using price estimate ${current_price:.2f} for {symbol} - should pass real price in decision!")

            # Calculate actual minimum USD (max of usd minimum and base_units minimum)
            usd_min = min_config['usd']
            base_units_min_usd = min_config['base_units'] * current_price
            min_size = max(usd_min, base_units_min_usd)

            # Use the larger of calculated size or minimum
            position_size_usd = max(calculated_size, min_size)

            # Safety: Check if we have enough remaining margin
            positions = await self._fetch_open_positions()
            current_positions = len(positions) if positions else 0

            # Estimate used margin from existing positions (rough - actual may vary)
            estimated_used_margin = sum(p.get('value', 0) / assumed_leverage for p in positions) if positions else 0
            remaining_margin = available_margin - estimated_used_margin

            if position_size_usd > remaining_margin * assumed_leverage and remaining_margin >= min_size / assumed_leverage:
                position_size_usd = remaining_margin * assumed_leverage  # Use whatever margin is left

            # Calculate actual margin that will be used
            actual_margin = position_size_usd / assumed_leverage

            # Log position sizing details with BOTH margin and notional
            used_minimum = position_size_usd == min_size
            status = "MIN OVERRIDE" if used_minimum else "CALCULATED"
            logger.info(
                f"💰 Position sizing: {symbol} | conf={confidence:.2f} | margin_pct={margin_pct*100:.0f}% | "
                f"notional=${position_size_usd:.2f} | margin=${actual_margin:.2f} ({actual_margin/account_balance*100:.1f}% of account) | "
                f"leverage=~{assumed_leverage:.0f}x [{status}]"
            )
        else:
            # Fallback to old approach if no balance or balance too small
            # With 50x leverage: $250 notional = $5 margin, $500 = $10 margin
            if confidence >= 0.8:
                position_size_usd = self.default_position_size * 2.0  # $500 notional = $10 margin
            elif confidence >= 0.6:
                position_size_usd = self.default_position_size * 1.5  # $375 notional = $7.50 margin
            else:
                position_size_usd = self.default_position_size  # $250 notional = $5 margin

            # IMPORTANT: Get current_price from decision (same as dynamic sizing block)
            current_price = decision.get('current_price')
            if not current_price:
                logger.warning(f"⚠️ Using price estimate for {symbol} in fallback sizing")
                price_estimates = {
                    'BTC': 101500.0,
                    'SOL': 155.0,
                    'ETH': 3400.0,
                }
                current_price = price_estimates.get(symbol, 100.0)

            if account_balance is None:
                logger.warning("Could not fetch balance - using default position sizing")
            else:
                logger.warning(f"Balance too small (${account_balance:.2f}) - using default position sizing")

        # Calculate quantity in base units (current_price already set above in dynamic sizing)
        # If not using dynamic sizing, use price estimate
        if 'current_price' not in locals():
            # Note: PacificaSDK doesn't have get_current_price() method
            # Use market price passed in decision or fallback to estimates
            logger.warning(f"⚠️ No price available for {symbol} - using fallback estimate")
            # Very basic fallback based on symbol type
            if 'BTC' in symbol or 'WBTC' in symbol:
                current_price = 100000.0
            elif 'ETH' in symbol:
                current_price = 3500.0
            elif 'SOL' in symbol:
                current_price = 200.0
            else:
                current_price = 1.0  # Conservative fallback

        # Get decimals - use sensible defaults based on asset type
        # Note: PacificaSDK doesn't store market metadata
        # Some tokens require integer lot sizes (like DOGE, SHIB, etc.)
        if symbol in ['BTC', 'WBTC']:
            decimals = 5  # BTC uses high precision
        elif symbol in ['ETH', 'WETH']:
            decimals = 4
        elif symbol in ['SOL', 'WSOL']:
            decimals = 2  # SOL lot size = 0.01
        elif symbol in ['DOGE', 'SHIB', 'PEPE', '1000PEPE', 'BONK', 'WIF', 'FLOKI']:
            decimals = 0  # Integer lot sizes only
        else:
            decimals = 3  # Default for most assets

        quantity = position_size_usd / current_price

        # Round to appropriate precision
        if decimals == 0:
            # For integer lot sizes, round to nearest integer
            quantity = round(quantity)
        else:
            quantity = round(quantity, decimals)

        logger.info(f"Position: ${position_size_usd:.2f} @ ~${current_price:.2f} = {quantity:.{decimals}f} {symbol} (decimals={decimals} from API)")

        # Dry-run mode
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would place {side} market order: {quantity:.{decimals}f} {symbol}")
            
            # Log simulated trade
            self.tracker.log_entry(
                order_id=None,
                symbol=symbol,
                side=side.lower(),
                size=quantity,
                entry_price=current_price,
                notes=f"[DRY-RUN] {reason}"
            )

            return {
                "success": True,
                "action": action,
                "symbol": symbol,
                "order_id": "DRY_RUN_ORDER",
                "filled_size": quantity,
                "filled_price": current_price,
                "error": None
            }

        # LIVE mode - place actual order
        try:
            # Check orderbook liquidity before placing order
            liquidity_check = await self.liquidity_checker.check_liquidity(
                symbol=symbol,
                side=side,
                size_usd=position_size_usd,
                current_price=current_price
            )

            if not liquidity_check.get('has_liquidity'):
                logger.warning(
                    f"⚠️  SKIPPING {side} {symbol} order - Insufficient liquidity\n"
                    f"   {liquidity_check.get('reason', 'Unknown reason')}\n"
                    f"   Available: ${liquidity_check.get('available_liquidity_usd', 0):.2f}, "
                    f"Required: ${position_size_usd:.2f} (depth ratio: {liquidity_check.get('depth_ratio', 0):.2f}x)"
                )
                return {
                    "success": False,
                    "action": action,
                    "symbol": symbol,
                    "size": quantity,
                    "message": f"Insufficient liquidity: {liquidity_check.get('reason')}",
                    "error": "INSUFFICIENT_LIQUIDITY"
                }

            logger.info(
                f"✅ Liquidity check passed: ${liquidity_check.get('available_liquidity_usd', 0):.2f} "
                f"available (ratio: {liquidity_check.get('depth_ratio', 0):.2f}x) for ${position_size_usd:.2f} order"
            )

            logger.info(f"[LIVE] Placing {side} market order: {quantity:.{decimals}f} {symbol}")

            # Note: SDK method is synchronous and only accepts: symbol, side, amount, slippage_percent, reduce_only, client_order_id
            order_result = self.sdk.create_market_order(
                symbol=symbol,
                side=sdk_side,
                amount=str(quantity),  # SDK expects string
                reduce_only=False
            )

            if not order_result or not order_result.get("success"):
                error = order_result.get("error", "Unknown error") if order_result else "No result returned"
                logger.error(f"Order failed: {error}")
                return {
                    "success": False,
                    "action": action,
                    "symbol": symbol,
                    "order_id": None,
                    "filled_size": None,
                    "filled_price": None,
                    "error": error
                }

            tx_hash = order_result.get("tx_hash")
            logger.info(f"✅ Order placed successfully: tx_hash={tx_hash}")

            # Log trade entry (use estimated price - actual fill price will be different)
            order_id = tx_hash or f"PACIFICA_{int(datetime.now().timestamp())}"
            self.tracker.log_entry(
                order_id=order_id,
                symbol=symbol,
                side=side.lower(),
                size=quantity,
                entry_price=current_price,  # Estimated - actual fill may differ
                notes=reason
            )

            return {
                "success": True,
                "action": action,
                "symbol": symbol,
                "order_id": order_id,
                "filled_size": quantity,
                "filled_price": current_price,  # Estimated
                "error": None
            }

        except Exception as e:
            logger.error(f"Exception placing order: {e}", exc_info=True)
            return {
                "success": False,
                "action": action,
                "symbol": symbol,
                "order_id": None,
                "filled_size": None,
                "filled_price": None,
                "error": f"Exception: {str(e)}"
            }

    async def _close_position(self, symbol: str, reason: str) -> Dict:
        """
        Close position for symbol

        Args:
            symbol: Market symbol
            reason: Close reason

        Returns:
            Execution result dict
        """
        logger.info(f"Closing position: {symbol}")

        # Get open positions
        positions = await self._fetch_open_positions()

        # Note: Pacifica SDK works with symbols directly, no market_id needed

        # Find position by symbol
        position = None
        for pos in positions:
            if pos.get('symbol') == symbol:
                position = pos
                logger.info(f"🔍 Found position for {symbol}: {pos}")
                break

        if not position:
            logger.warning(f"No open position found for {symbol}")
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "error": f"No open position for {symbol}"
            }

        # Close by placing opposite order
        # Use size_raw if available (has sign), otherwise use size/amount (absolute value)
        # Note: Pacifica API returns 'amount' as a string, so convert to float
        size_raw = position.get('size_raw', position.get('size', position.get('amount', 0)))
        size_raw = float(size_raw) if size_raw else 0
        size = abs(size_raw)
        
        if size == 0:
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "error": "Position size is zero"
            }

        # Determine position type from Pacifica's 'side' field:
        # - 'bid' = LONG position (bought to open)
        # - 'ask' = SHORT position (sold to open)
        position_side = position.get('side', 'bid')
        is_long = (position_side == 'bid')

        # To close: LONG position (bid) needs SELL order (ask), SHORT position (ask) needs BUY order (bid)
        side = "ask" if is_long else "bid"
        action_str = "SELL" if is_long else "BUY"
        
        position_type = "LONG" if is_long else "SHORT"
        logger.info(f"Closing {symbol} {position_type} position: {size} (side: {side}, reduce_only=True)")

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would close {symbol} position")

            # Find and close in tracker
            open_trades = self.tracker.get_open_trades()
            for trade in open_trades:
                if trade.get('symbol') == symbol and trade.get('status') == 'open':
                    # Convert entry_price to float (API returns strings)
                    exit_price = float(position.get('entry_price', 0))
                    self.tracker.log_exit(
                        order_id=trade.get('order_id', ''),
                        exit_price=exit_price,
                        exit_reason=reason,
                        fees=0.0
                    )
                    break

            return {
                "success": True,
                "action": "CLOSE",
                "symbol": symbol,
                "order_id": "DRY_RUN_CLOSE",
                "filled_size": size,
                "filled_price": float(position.get('entry_price', 0)),  # Convert to float
                "error": None
            }

        # LIVE mode - close position
        try:
            # Note: Pacifica SDK uses market orders, price is determined by orderbook
            logger.info(f"📤 Placing close order: {symbol} | {side} | {size} | reduce_only=True")

            # Note: SDK method is synchronous and only accepts: symbol, side, amount, slippage_percent, reduce_only, client_order_id
            order_result = self.sdk.create_market_order(
                symbol=symbol,
                side=side,
                amount=str(size),  # SDK expects string
                reduce_only=True  # Close position, don't open new one
            )

            logger.info(f"📥 Order result: {order_result}")

            if not order_result or not order_result.get("success"):
                error = order_result.get("error", "Unknown error") if order_result else "No result returned"
                logger.error(f"❌ Close order failed: {error}")
                return {
                    "success": False,
                    "action": "CLOSE",
                    "symbol": symbol,
                    "error": error
                }

            tx_hash = order_result.get("tx_hash")
            logger.info(f"✅ Close order placed: tx_hash={tx_hash}")
            
            # Verify position was actually closed
            # Also wait a bit to ensure nonce is consumed before next order
            await asyncio.sleep(2.5)  # Wait for order to settle AND nonce to be consumed
            verify_positions = await self._fetch_open_positions()
            still_open = any(p.get('symbol') == symbol for p in verify_positions)
            if still_open:
                logger.warning(f"⚠️ Position {symbol} still open after close order! Order may not have executed.")
            else:
                logger.info(f"✅ Position {symbol} confirmed closed")

            # Update tracker
            open_trades = self.tracker.get_open_trades()
            for trade in open_trades:
                if trade.get('symbol') == symbol and trade.get('status') == 'open':
                    # Convert entry_price to float (Pacifica API returns strings)
                    exit_price = float(position.get('entry_price', 0))  # Estimated
                    self.tracker.log_exit(
                        order_id=trade.get('order_id', ''),
                        exit_price=exit_price,
                        exit_reason=reason,
                        fees=0.0
                    )
                    break

            return {
                "success": True,
                "action": "CLOSE",
                "symbol": symbol,
                "order_id": tx_hash or f"CLOSE_{int(datetime.now().timestamp())}",
                "filled_size": size,
                "filled_price": position.get('entry_price', 0),
                "error": None
            }

        except Exception as e:
            logger.error(f"Exception closing position: {e}", exc_info=True)
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "error": f"Exception: {str(e)}"
            }
