"""
Hibachi Trade Executor
Executes LLM trading decisions using Hibachi SDK

Mirrors Lighter TradeExecutor structure but adapted for Hibachi DEX
"""

import logging
import sys
import os
import asyncio
from typing import Optional, Dict
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trade_tracker import TradeTracker

logger = logging.getLogger(__name__)


class HibachiTradeExecutor:
    """
    Execute LLM trading decisions for Hibachi DEX

    Args:
        hibachi_sdk: HibachiSDK instance for order placement
        trade_tracker: TradeTracker instance for logging
        dry_run: If True, don't actually place orders (default: False)
        default_position_size: Default position size in USD (default: $2 for $58 account)
        max_positions: Max open positions (default: 10)
    """

    def __init__(
        self,
        hibachi_sdk,  # HibachiSDK instance
        trade_tracker: TradeTracker,
        dry_run: bool = False,
        default_position_size: float = 5.0,  # $5 per trade (~8% of $58 account)
        max_positions: int = 10,
        max_position_age_minutes: int = 240  # 4 hours (same as Lighter)
    ):
        self.sdk = hibachi_sdk
        self.tracker = trade_tracker
        self.dry_run = dry_run
        self.default_position_size = default_position_size
        self.max_positions = max_positions
        self.max_position_age_minutes = max_position_age_minutes

        mode = "DRY-RUN" if dry_run else "LIVE"
        logger.info(f"✅ HibachiTradeExecutor initialized ({mode} mode, ${default_position_size}/trade, Max Age: {max_position_age_minutes}min)")

    async def _fetch_account_balance(self) -> Optional[float]:
        """Fetch account balance from Hibachi API"""
        return await self.sdk.get_balance()

    async def _fetch_open_positions(self):
        """Fetch current open positions from Hibachi API"""
        try:
            positions = await self.sdk.get_positions()
            return positions if positions else []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def check_stale_positions(self):
        """
        Check for stale positions and close them to free up capital

        Returns:
            List of closed position symbols
        """
        closed_symbols = []

        try:
            positions = await self._fetch_open_positions()

            if not positions:
                logger.debug("No open positions to check")
                return closed_symbols

            for position in positions:
                symbol = position.get('symbol')
                quantity = float(position.get('quantity', 0))
                direction = position.get('direction')

                # Skip if no quantity
                if quantity == 0:
                    continue

                # Check position age from tracker
                tracker_position = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_position:
                    open_time = tracker_position.get('timestamp')
                    if open_time:
                        age_minutes = (datetime.now() - open_time).total_seconds() / 60

                        if age_minutes > self.max_position_age_minutes:
                            logger.info(f"🕐 Position {symbol} aged out ({age_minutes:.0f} min > {self.max_position_age_minutes} min limit)")
                            result = await self._close_position(symbol, f"Aged {age_minutes:.0f} min (limit: {self.max_position_age_minutes} min)")
                            if result.get('success'):
                                closed_symbols.append(symbol)

        except Exception as e:
            logger.error(f"Error checking stale positions: {e}")

        return closed_symbols

    async def execute_decision(self, decision: Dict) -> Dict:
        """
        Execute LLM trading decision

        Args:
            decision: Dict with 'action', 'symbol', 'reasoning'

        Returns:
            Dict with execution result
        """
        action = decision.get('action')
        symbol = decision.get('symbol')
        reasoning = decision.get('reasoning', 'No reason provided')

        logger.info(f"🎯 Executing decision: {action} {symbol} - {reasoning}")

        # Fetch current positions
        positions = await self._fetch_open_positions()
        open_position_count = len([p for p in positions if float(p.get('quantity', 0)) > 0])

        # Check position limits
        if action in ['LONG', 'SHORT'] and open_position_count >= self.max_positions:
            logger.warning(f"⚠️  Max positions reached ({open_position_count}/{self.max_positions})")
            return {
                'success': False,
                'action': action,
                'symbol': symbol,
                'error': 'Max positions reached'
            }

        # Execute based on action
        if action in ['LONG', 'SHORT']:
            return await self._open_position(action, symbol, reasoning, decision)
        elif action == 'CLOSE':
            return await self._close_position(symbol, reasoning)
        elif action == 'HOLD':
            logger.info(f"✋ HOLD {symbol} - {reasoning}")
            return {
                'success': True,
                'action': 'HOLD',
                'symbol': symbol,
                'reasoning': reasoning
            }
        else:
            logger.warning(f"⚠️  Unknown action: {action}")
            return {
                'success': False,
                'action': action,
                'symbol': symbol,
                'error': f'Unknown action: {action}'
            }

    async def _open_position(self, action: str, symbol: str, reason: str, decision: Dict = None) -> Dict:
        """
        Open a new position

        Args:
            action: "LONG" or "SHORT"
            symbol: Trading symbol
            reason: Reasoning for the trade
            decision: Full decision dict

        Returns:
            Dict with execution result
        """
        try:
            # Get current price
            price = await self.sdk.get_price(symbol)
            if not price:
                logger.error(f"❌ Cannot get price for {symbol}")
                return {
                    'success': False,
                    'action': action,
                    'symbol': symbol,
                    'error': 'Cannot get price'
                }

            # DYNAMIC POSITION SIZING (mirrors Lighter bot approach)
            # Scale position size based on account balance and confidence
            confidence = decision.get('confidence', 0.5) if decision else 0.5
            account_balance = await self._fetch_account_balance()

            if account_balance and account_balance > 1.0:
                # Reserve 15% of account for safety
                reserve_pct = 0.15
                available_capital = account_balance * (1 - reserve_pct)

                # Confidence-based position sizing (% of available capital)
                # Aggressive scalping: use more capital per trade
                if confidence < 0.5:
                    position_pct = 0.08   # 8% of available
                elif confidence < 0.7:
                    position_pct = 0.12  # 12% of available
                elif confidence < 0.85:
                    position_pct = 0.15  # 15% of available
                else:
                    position_pct = 0.20  # 20% of available (high confidence)

                # Calculate position size
                calculated_size = available_capital * position_pct

                # Minimum $3, maximum 25% of account per position
                min_size = 3.0
                max_size = account_balance * 0.25
                position_size_usd = max(min_size, min(calculated_size, max_size))

                # Check remaining capacity (don't overextend)
                positions = await self._fetch_open_positions()
                current_positions = len([p for p in positions if float(p.get('quantity', 0)) > 0]) if positions else 0

                if current_positions >= self.max_positions:
                    logger.warning(f"⚠️ Max positions ({self.max_positions}) reached")

                logger.info(
                    f"💰 Dynamic sizing: ${account_balance:.2f} balance | "
                    f"conf={confidence:.2f} → {position_pct*100:.0f}% = ${position_size_usd:.2f} "
                    f"({position_size_usd/account_balance*100:.1f}% of account)"
                )
            else:
                # Fallback to default if can't fetch balance
                position_size_usd = self.default_position_size
                if account_balance is None:
                    logger.warning("Could not fetch balance - using default position sizing")
                else:
                    logger.warning(f"Balance too small (${account_balance:.2f}) - using default sizing")

            amount = position_size_usd / price

            # Get market info to round properly
            markets = await self.sdk.get_markets()
            market = next((m for m in markets if m['symbol'] == symbol), None)

            if not market:
                logger.error(f"❌ Market {symbol} not found")
                return {
                    'success': False,
                    'action': action,
                    'symbol': symbol,
                    'error': 'Market not found'
                }

            # Round to step size
            step_size = float(market.get('stepSize', 0.00000001))
            amount = round(amount / step_size) * step_size

            is_buy = (action == "LONG")

            logger.info(f"{'📈' if is_buy else '📉'} {action} {symbol}: {amount:.8f} @ ${price:.2f} (${position_size_usd:.2f})")
            logger.info(f"   Reason: {reason}")

            if self.dry_run:
                logger.info(f"🏃 DRY-RUN: Would place {action} order for {amount:.8f} {symbol}")

                # Record in tracker
                self.tracker.log_entry(
                    order_id=None,
                    symbol=symbol,
                    side=action.lower(),
                    entry_price=price,
                    size=amount,
                    notes=reason
                )

                return {
                    'success': True,
                    'action': action,
                    'symbol': symbol,
                    'price': price,
                    'amount': amount,
                    'dry_run': True
                }

            # Execute real order
            order = await self.sdk.create_market_order(symbol, is_buy, amount)

            if order:
                logger.info(f"✅ Order placed: {order}")

                # Record in tracker
                self.tracker.log_entry(
                    order_id=order.get('orderId'),
                    symbol=symbol,
                    side=action.lower(),
                    entry_price=price,
                    size=amount,
                    notes=reason
                )

                return {
                    'success': True,
                    'action': action,
                    'symbol': symbol,
                    'price': price,
                    'amount': amount,
                    'order': order
                }
            else:
                logger.error(f"❌ Order failed for {symbol}")
                return {
                    'success': False,
                    'action': action,
                    'symbol': symbol,
                    'error': 'Order execution failed'
                }

        except Exception as e:
            logger.error(f"❌ Error opening position for {symbol}: {e}")
            return {
                'success': False,
                'action': action,
                'symbol': symbol,
                'error': str(e)
            }

    async def _close_position(self, symbol: str, reason: str) -> Dict:
        """
        Close an existing position

        Args:
            symbol: Trading symbol
            reason: Reasoning for closing

        Returns:
            Dict with execution result
        """
        try:
            # Get current position
            positions = await self._fetch_open_positions()
            position = next((p for p in positions if p.get('symbol') == symbol), None)

            if not position:
                logger.warning(f"⚠️  No position found for {symbol}")
                return {
                    'success': False,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'error': 'No position found'
                }

            quantity = float(position.get('quantity', 0))
            direction = position.get('direction')

            if quantity == 0:
                logger.warning(f"⚠️  Position {symbol} has zero quantity")
                return {
                    'success': False,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'error': 'Zero quantity'
                }

            # Close position (opposite of current direction)
            is_buy = (direction == 'Short')  # If short, buy to close

            logger.info(f"🔴 CLOSE {symbol}: {quantity:.8f} (Direction: {direction})")
            logger.info(f"   Reason: {reason}")

            if self.dry_run:
                logger.info(f"🏃 DRY-RUN: Would close {symbol} position")

                # Get tracker position for PnL
                tracker_pos = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_pos:
                    order_id = tracker_pos.get('order_id')
                    self.tracker.log_exit(
                        order_id=order_id,
                        exit_price=0,  # Don't have real price in dry-run
                        exit_reason=reason
                    )

                return {
                    'success': True,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'quantity': quantity,
                    'dry_run': True
                }

            # Execute real close order
            order = await self.sdk.create_market_order(symbol, is_buy, quantity)

            if order:
                logger.info(f"✅ Position closed: {order}")

                # Get tracker position for PnL
                tracker_pos = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_pos:
                    price = await self.sdk.get_price(symbol)
                    order_id = tracker_pos.get('order_id')
                    self.tracker.log_exit(
                        order_id=order_id,
                        exit_price=price if price else 0,
                        exit_reason=reason
                    )

                return {
                    'success': True,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'quantity': quantity,
                    'order': order
                }
            else:
                logger.error(f"❌ Close order failed for {symbol}")
                return {
                    'success': False,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'error': 'Close order failed'
                }

        except Exception as e:
            logger.error(f"❌ Error closing position for {symbol}: {e}")
            return {
                'success': False,
                'action': 'CLOSE',
                'symbol': symbol,
                'error': str(e)
            }
