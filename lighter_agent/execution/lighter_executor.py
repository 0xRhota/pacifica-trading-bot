"""
Lighter Trade Executor
Executes LLM trading decisions using Lighter SDK

Mirrors Pacifica TradeExecutor structure but adapted for Lighter DEX
"""

import logging
import sys
import os
import asyncio
from typing import Optional, Dict
from datetime import datetime
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trade_tracker import TradeTracker
from lighter_agent.data.liquidity_checker import LiquidityChecker

logger = logging.getLogger(__name__)


class LighterTradeExecutor:
    """
    Execute LLM trading decisions for Lighter DEX

    Args:
        lighter_sdk: LighterSDK instance for order placement
        trade_tracker: TradeTracker instance for logging
        dry_run: If True, don't actually place orders (default: False)
        default_position_size: Default position size in USD (default: $5 for $100 account)
        max_positions: Max open positions (default: 3)
    """

    # NO HARDCODED MAPPINGS - All market data fetched dynamically from SDK

    def __init__(
        self,
        lighter_sdk,  # LighterSDK instance
        trade_tracker: TradeTracker,
        dry_run: bool = False,
        default_position_size: float = 5.0,  # $5 per trade for $100 account
        max_positions: int = 15,
        max_position_age_minutes: int = 60,  # Nov 7 insight: Quick exits work
        favor_zk_zec: bool = True  # Nov 7 insight: ZK (76.5%) and ZEC (63.6%) win rates
    ):
        self.sdk = lighter_sdk
        self.tracker = trade_tracker
        self.dry_run = dry_run
        self.default_position_size = default_position_size
        self.max_positions = max_positions
        self.liquidity_checker = LiquidityChecker(lighter_sdk)

        # Nov 7 learnings: Position aging and symbol weighting
        self.max_position_age_minutes = max_position_age_minutes
        self.favor_zk_zec = favor_zk_zec

        # Nov 7 historical win rates (for position sizing)
        self.historical_win_rates = {
            'ZK': 0.765,   # 76.5% win rate on Nov 7
            'ZEC': 0.636,  # 63.6% win rate on Nov 7
            'CRV': 0.800,  # 80% win rate on Nov 7
            'XRP': 1.000,  # 100% win rate (small sample)
            'AAVE': 0.833  # 83.3% win rate on Nov 7
        }
        self.baseline_win_rate = 0.506  # Nov 7 overall: 50.6%

        mode = "DRY-RUN" if dry_run else "LIVE"
        aging_info = f", Max Age: {max_position_age_minutes}min" if max_position_age_minutes < 9999 else ""
        zk_info = ", Favor ZK/ZEC: ON" if favor_zk_zec else ""
        logger.info(f"✅ LighterTradeExecutor initialized ({mode} mode, ${default_position_size}/trade{aging_info}{zk_info})")

    async def _fetch_account_balance(self) -> Optional[float]:
        """Fetch account balance from Lighter API"""
        return await self.sdk.get_balance()

    async def _fetch_open_positions(self):
        """Fetch current open positions from Lighter API"""
        try:
            result = await self.sdk.get_positions()
            if result.get("success") and result.get("data"):
                return result["data"]
            return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def check_stale_positions(self):
        """
        Check for stale positions and close them to free up capital

        Based on Nov 7 analysis: Quick exits work (avg hold 244 min, but many wins < 60 min)
        Position aging encourages capital rotation into fresh opportunities

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
        Execute LLM trading decision (async for Lighter)

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

        # Get market ID dynamically from SDK
        market_id = await self.sdk.get_market_id_for_symbol(symbol)
        if not market_id:
            logger.error(f"❌ Market ID not found for {symbol} - symbol not available on Lighter")
            return {
                "success": False,
                "action": action,
                "symbol": symbol,
                "error": f"Unknown symbol: {symbol} (not available on Lighter)"
            }

        # Get current price (approximate - Lighter uses market orders)
        # For scalping strategy, use small fixed position sizes
        confidence = decision.get("confidence", 0.5)

        # Get account balance for dynamic sizing
        account_balance = await self._fetch_account_balance()

        # Nov 7 learning: Apply symbol weighting multiplier
        # ZK: 76.5% win rate → 1.51x multiplier
        # ZEC: 63.6% win rate → 1.26x multiplier
        symbol_multiplier = 1.0
        if self.favor_zk_zec and symbol in self.historical_win_rates:
            historical_rate = self.historical_win_rates[symbol]
            symbol_multiplier = historical_rate / self.baseline_win_rate
            logger.info(
                f"📊 Symbol weighting: {symbol} has {historical_rate*100:.1f}% historical win rate "
                f"(baseline {self.baseline_win_rate*100:.1f}%) → {symbol_multiplier:.2f}x multiplier"
            )

        # LEVERAGE-AWARE POSITION SIZING (Margin-Based)
        # Think in terms of MARGIN USAGE (% of account), not notional value
        # With perps, we can use 5-10x leverage to amplify position size
        if account_balance and account_balance > 1.0:
            # Conservative default leverage assumption (actual varies by market)
            # NEAR=10x, RESOLV=3x, etc - using 5x as safe middle ground
            assumed_leverage = 5.0

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

            # Apply symbol weighting multiplier (Nov 7 learning)
            calculated_size = calculated_size * symbol_multiplier

            # Default exchange minimums (used as fallback if no metadata available)
            # Most Lighter markets have $10 minimum
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
            if confidence >= 0.8:
                position_size_usd = self.default_position_size * 2.0  # $10
            elif confidence >= 0.6:
                position_size_usd = self.default_position_size * 1.5  # $7.50
            else:
                position_size_usd = self.default_position_size  # $5

            if account_balance is None:
                logger.warning("Could not fetch balance - using default position sizing")
            else:
                logger.warning(f"Balance too small (${account_balance:.2f}) - using default position sizing")

        # Calculate quantity in base units (current_price already set above in dynamic sizing)
        # If not using dynamic sizing, use price estimate
        if 'current_price' not in locals():
            # Fetch real-time price from SDK instead of hardcoded estimates
            current_price = await self.sdk.get_current_price(symbol, market_id=market_id)
            if not current_price:
                logger.warning(f"⚠️ Could not fetch price for {symbol} - using fallback estimate")
                # Very basic fallback based on symbol type
                if 'BTC' in symbol or 'WBTC' in symbol:
                    current_price = 100000.0
                elif 'ETH' in symbol:
                    current_price = 3500.0
                elif 'SOL' in symbol:
                    current_price = 200.0
                else:
                    current_price = 1.0  # Conservative fallback

        # Get decimals dynamically from SDK metadata
        if self.sdk._market_metadata and market_id in self.sdk._market_metadata:
            decimals = self.sdk._market_metadata[market_id].get('size_decimals', 3)
        else:
            logger.warning(f"⚠️ No metadata found for {symbol} (market_id={market_id}), using default decimals=3")
            decimals = 3

        quantity = position_size_usd / current_price

        # Round to appropriate precision
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
                current_price=current_price,
                market_id=market_id
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

            order_result = await self.sdk.create_market_order(
                symbol=symbol,
                side=sdk_side,
                amount=quantity,
                market_id=market_id,  # Required for dynamic markets
                decimals=decimals,  # Pass calculated decimals
                current_price=current_price  # Pass real-time price to avoid extreme values
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
            order_id = tx_hash or f"LIGHTER_{int(datetime.now().timestamp())}"
            self.tracker.log_entry(
                order_id=order_id,
                symbol=symbol,
                side=side.lower(),
                size=quantity,
                entry_price=current_price,  # Estimated - actual fill may differ
                notes=reason,
                confidence=confidence  # Store confidence for hold logic
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

        # Find market ID dynamically from SDK
        market_id = await self.sdk.get_market_id_for_symbol(symbol)
        if not market_id:
            logger.error(f"❌ Market ID not found for {symbol} - symbol not available on Lighter")
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "error": f"Unknown symbol: {symbol} (not available on Lighter)"
            }

        # Find position
        position = None
        for pos in positions:
            if pos.get('market_id') == market_id:
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
        # Use size_raw if available (has sign), otherwise use size (absolute value)
        size_raw = position.get('size_raw', position.get('size', 0))
        size = abs(size_raw)
        
        if size == 0:
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "error": "Position size is zero"
            }

        # Determine side: use is_long from position if available, otherwise check sign
        is_long = position.get('is_long', size_raw > 0) if 'is_long' in position else (size_raw > 0)
        
        # To close: LONG position needs SELL (ask), SHORT position needs BUY (bid)
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
                    exit_price = position.get('entry_price', 0)  # Use entry price as estimate
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
                "filled_price": position.get('entry_price', 0),
                "error": None
            }

        # LIVE mode - close position
        try:
            # Get current market price for reduce-only order
            # CRITICAL FIX: Use REAL-TIME price instead of stale entry_price
            # Fetch from 1m candles API for most accurate current price
            current_price = await self.sdk.get_current_price(symbol, market_id=market_id)

            if current_price:
                entry_price = position.get('entry_price', 0)
                logger.info(f"💲 Using real-time price for {symbol}: ${current_price:.4f} (entry was ${entry_price:.4f})")
            else:
                # Fallback to entry_price if real-time fetch fails
                current_price = position.get('entry_price', None)
                if current_price:
                    logger.warning(f"⚠️ Real-time price fetch failed for {symbol}, using stale entry_price: ${current_price:.4f}")
                else:
                    logger.warning(f"⚠️ No price available for {symbol}, will use SDK fallback")

            # Use reduce_only=True to actually close the position, not open a new one
            logger.info(f"📤 Placing close order: {symbol} | {side} | {size} | reduce_only=True | price=${current_price if current_price else 'fallback'}")
            order_result = await self.sdk.create_market_order(
                symbol=symbol,
                side=side,
                amount=size,
                reduce_only=True,  # CRITICAL: Must be True to close, not open new position
                market_id=market_id,  # CRITICAL: Pass market_id for dynamic decimal lookup
                current_price=current_price  # CRITICAL FIX: Pass current price for reduce-only
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
            still_open = any(p.get('market_id') == market_id for p in verify_positions)
            if still_open:
                logger.warning(f"⚠️ Position {symbol} still open after close order! Order may not have executed.")
            else:
                logger.info(f"✅ Position {symbol} confirmed closed")

            # Update tracker
            open_trades = self.tracker.get_open_trades()
            for trade in open_trades:
                if trade.get('symbol') == symbol and trade.get('status') == 'open':
                    exit_price = position.get('entry_price', 0)  # Estimated
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
