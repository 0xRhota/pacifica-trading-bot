"""
Paradex Trade Executor
Handles order placement and position management on Paradex

Zero-fee exchange - focus on minimizing slippage by checking spreads
Includes fill verification to detect orders accepted but not filled (margin issues)
"""

import logging
import time
import asyncio
from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ParadexTradeExecutor:
    """
    Execute trades on Paradex DEX
    """

    def __init__(
        self,
        paradex_client,
        trade_tracker,
        data_fetcher,
        dry_run: bool = True,
        default_position_size: float = 10.0,
        max_positions: int = 10,
        max_spread_pct: float = 0.1  # Max acceptable spread for market orders
    ):
        """
        Initialize Paradex executor

        Args:
            paradex_client: ParadexSubkey instance
            trade_tracker: TradeTracker instance
            data_fetcher: ParadexDataFetcher instance
            dry_run: If True, simulate trades
            default_position_size: USD per trade
            max_positions: Maximum open positions
            max_spread_pct: Max spread to accept for market orders
        """
        self.client = paradex_client
        self.tracker = trade_tracker
        self.fetcher = data_fetcher
        self.dry_run = dry_run
        self.position_size = default_position_size
        self.max_positions = max_positions
        self.max_spread_pct = max_spread_pct

        # Import order types
        from paradex_py.common.order import Order, OrderType, OrderSide
        self.Order = Order
        self.OrderType = OrderType
        self.OrderSide = OrderSide

    def _get_full_symbol(self, symbol: str) -> str:
        """Convert base symbol to full Paradex symbol"""
        if symbol.endswith('-USD-PERP'):
            return symbol
        return f"{symbol}-USD-PERP"

    def _get_position_size(self, symbol: str) -> float:
        """
        Get current position size for a symbol

        Args:
            symbol: Base symbol (e.g., "BTC")

        Returns:
            Position size (positive for long, negative for short, 0 if none)
        """
        positions = self.fetcher.fetch_positions()
        for pos in positions:
            if pos.get('symbol') == symbol:
                size = float(pos.get('size', 0))
                side = pos.get('side', 'LONG')
                return size if side == 'LONG' else -size
        return 0.0

    async def _verify_order_fill(
        self,
        symbol: str,
        expected_change: float,
        position_before: float,
        max_wait_seconds: float = 3.0
    ) -> Dict:
        """
        Verify that an order actually filled by checking position change

        Args:
            symbol: Base symbol
            expected_change: Expected position change (positive for buy, negative for sell)
            position_before: Position size before order was placed
            max_wait_seconds: Maximum time to wait for fill confirmation

        Returns:
            Dict with 'filled' boolean and details
        """
        # Wait briefly for order to process
        await asyncio.sleep(0.5)

        # Check position multiple times
        checks = int(max_wait_seconds / 0.5)
        for i in range(checks):
            position_after = self._get_position_size(symbol)
            actual_change = position_after - position_before

            # Check if position changed in expected direction (80% tolerance for partial fills)
            if expected_change > 0:  # Buy order
                if actual_change > expected_change * 0.8:
                    logger.info(f"✅ Order VERIFIED: position changed {position_before:.6f} → {position_after:.6f}")
                    return {'filled': True, 'position_after': position_after, 'actual_change': actual_change}
            else:  # Sell order
                if actual_change < expected_change * 0.8:
                    logger.info(f"✅ Order VERIFIED: position changed {position_before:.6f} → {position_after:.6f}")
                    return {'filled': True, 'position_after': position_after, 'actual_change': actual_change}

            if i < checks - 1:
                await asyncio.sleep(0.5)

        # Order did not fill
        logger.error(f"❌ Order NOT FILLED: position unchanged at {position_before:.6f} (expected change: {expected_change:.6f})")
        return {
            'filled': False,
            'error': 'Order accepted but not filled - likely rejected due to insufficient margin',
            'position_before': position_before,
            'position_after': self._get_position_size(symbol)
        }

    def _calculate_order_size(self, symbol: str, usd_amount: float) -> Optional[Decimal]:
        """
        Calculate order size based on USD amount and current price

        Args:
            symbol: Base symbol (e.g., "ETH")
            usd_amount: USD amount to trade

        Returns:
            Order size in base currency or None if error
        """
        bbo = self.fetcher.fetch_bbo(symbol)
        if not bbo or bbo.get('mid_price', 0) <= 0:
            logger.error(f"Cannot get price for {symbol}")
            return None

        price = bbo['mid_price']
        size = usd_amount / price

        # Get market info for step size
        market_info = self.fetcher.market_info.get(symbol, {})
        step_size = market_info.get('step_size', 0.0001)
        min_notional = market_info.get('min_notional', 10)  # min USD value

        # Check if notional is above minimum
        if usd_amount < min_notional:
            logger.warning(f"Order notional ${usd_amount} below minimum ${min_notional} for {symbol}")
            return None

        # Round to step size (important: some tokens like DOGE require whole numbers)
        if step_size >= 1:
            # Integer step sizes (DOGE, PUMP, etc.) - round to whole number
            size = max(1, int(size))
        elif step_size > 0:
            # Fractional step sizes - round properly
            size = float(int(size / step_size) * step_size)

        logger.debug(f"{symbol}: size={size}, step_size={step_size}")
        return Decimal(str(size))

    def _check_spread(self, symbol: str) -> tuple[bool, float]:
        """
        Check if spread is acceptable for market order

        Returns:
            (is_acceptable, spread_pct)
        """
        bbo = self.fetcher.fetch_bbo(symbol)
        if not bbo:
            return False, 999

        spread_pct = bbo.get('spread_pct', 999)
        is_acceptable = spread_pct <= self.max_spread_pct
        return is_acceptable, spread_pct

    async def execute_decision(self, decision: Dict) -> Dict:
        """
        Execute a trading decision

        Args:
            decision: Dict with keys:
                - action: "BUY", "SELL", "CLOSE"
                - symbol: Base symbol
                - confidence: 0.0-1.0
                - reason: String

        Returns:
            Dict with execution result
        """
        action = decision.get('action', '').upper()
        symbol = decision.get('symbol')
        confidence = decision.get('confidence', 0.5)
        reason = decision.get('reason', '')

        if not symbol:
            return {'success': False, 'error': 'No symbol provided'}

        if action == 'NOTHING':
            return {'success': True, 'action': 'NOTHING', 'message': 'No action taken'}

        # Check spread before market order
        is_ok, spread_pct = self._check_spread(symbol)
        if not is_ok and action in ['BUY', 'SELL']:
            logger.warning(f"Spread too wide for {symbol}: {spread_pct:.3f}% > {self.max_spread_pct}%")
            return {
                'success': False,
                'error': f'Spread too wide: {spread_pct:.3f}%',
                'action': action,
                'symbol': symbol
            }

        if action == 'BUY':
            return await self._open_position(symbol, 'LONG', confidence, reason)
        elif action == 'SELL':
            return await self._open_position(symbol, 'SHORT', confidence, reason)
        elif action == 'CLOSE':
            return await self._close_position(symbol, reason)
        else:
            return {'success': False, 'error': f'Unknown action: {action}'}

    async def _open_position(
        self,
        symbol: str,
        side: str,
        confidence: float,
        reason: str
    ) -> Dict:
        """
        Open a new position

        Args:
            symbol: Base symbol
            side: "LONG" or "SHORT"
            confidence: Confidence score
            reason: Trade reason

        Returns:
            Execution result
        """
        full_symbol = self._get_full_symbol(symbol)

        # Check if already have position
        positions = self.fetcher.fetch_positions()
        for pos in positions:
            if pos.get('symbol') == symbol:
                return {
                    'success': False,
                    'error': f'Already have position in {symbol}',
                    'action': 'BUY' if side == 'LONG' else 'SELL',
                    'symbol': symbol
                }

        # Check max positions
        if len(positions) >= self.max_positions:
            return {
                'success': False,
                'error': f'Max positions ({self.max_positions}) reached',
                'action': 'BUY' if side == 'LONG' else 'SELL',
                'symbol': symbol
            }

        # Dynamic position sizing based on account balance and confidence
        # Zero fees = maximize volume, scale with confidence for better entries
        account = self.fetcher.fetch_account_summary()
        account_balance = account.get('account_value', 0) if account else 0

        if account_balance and account_balance > 10:
            # Confidence-based leverage scaling (matches Hibachi)
            if confidence < 0.7:
                leverage = 4.0   # Decent setup
                base_pct = 0.50
            elif confidence < 0.8:
                leverage = 5.0   # Good setup
                base_pct = 0.60
            elif confidence < 0.9:
                leverage = 4.0   # High conf but risky
                base_pct = 0.50
            else:
                leverage = 3.0   # Very high conf = overconfidence trap
                base_pct = 0.40

            usd_amount = account_balance * base_pct * leverage
            usd_amount = max(50.0, min(usd_amount, 300.0))  # $50-300 range
            logger.info(f"📊 Dynamic sizing: ${account_balance:.0f} × {base_pct:.0%} × {leverage}x = ${usd_amount:.2f}")
        else:
            usd_amount = max(self.position_size, 15.0)  # Fallback to $15 minimum

        size = self._calculate_order_size(symbol, usd_amount)

        if not size:
            return {
                'success': False,
                'error': 'Cannot calculate order size',
                'action': 'BUY' if side == 'LONG' else 'SELL',
                'symbol': symbol
            }

        # Get current price for tracking
        bbo = self.fetcher.fetch_bbo(symbol)
        entry_price = bbo.get('mid_price', 0) if bbo else 0

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would {side} {size} {symbol} @ ~${entry_price:.4f} (${usd_amount:.2f})")
            # Track in trade tracker
            self.tracker.log_entry(
                order_id=f"dry_{symbol}_{int(time.time())}",
                symbol=symbol,
                side=side.lower(),
                entry_price=entry_price,
                size=float(size),
                confidence=confidence,
                notes=reason
            )
            return {
                'success': True,
                'action': 'BUY' if side == 'LONG' else 'SELL',
                'symbol': symbol,
                'size': float(size),
                'price': entry_price,
                'dry_run': True
            }

        # Fill verification and retry logic (same as Hibachi)
        max_retries = 3
        current_size = size
        current_usd = usd_amount

        # Get position BEFORE placing order
        position_before = self._get_position_size(symbol)

        for attempt in range(max_retries + 1):
            try:
                # Place market order
                order = self.Order(
                    market=full_symbol,
                    order_type=self.OrderType.Market,
                    order_side=self.OrderSide.Buy if side == 'LONG' else self.OrderSide.Sell,
                    size=current_size,
                )

                result = self.client.api_client.submit_order(order)

                if result.get('status') in ['NEW', 'FILLED']:
                    logger.info(f"📝 Order accepted by API - verifying fill...")

                    # CRITICAL: Verify the order actually filled
                    expected_change = float(current_size) if side == 'LONG' else -float(current_size)
                    verify_result = await self._verify_order_fill(
                        symbol=symbol,
                        expected_change=expected_change,
                        position_before=position_before,
                        max_wait_seconds=3.0
                    )

                    if verify_result.get('filled'):
                        # Order actually filled!
                        logger.info(f"✅ Order FILLED: {side} {current_size} {symbol} @ ~${entry_price:.4f}")

                        # Track in trade tracker
                        self.tracker.log_entry(
                            order_id=result.get('id'),
                            symbol=symbol,
                            side=side.lower(),
                            entry_price=entry_price,
                            size=float(current_size),
                            confidence=confidence,
                            notes=reason
                        )

                        return {
                            'success': True,
                            'action': 'BUY' if side == 'LONG' else 'SELL',
                            'symbol': symbol,
                            'size': float(current_size),
                            'price': entry_price,
                            'order_id': result.get('id')
                        }
                    else:
                        # Order was accepted but NOT filled - likely margin rejection
                        logger.error(f"❌ Order NOT FILLED for {symbol}: {verify_result.get('error', 'unknown')}")

                        if attempt < max_retries:
                            # Reduce size by 50% and retry
                            current_usd *= 0.5
                            current_size = self._calculate_order_size(symbol, current_usd)
                            if not current_size:
                                break
                            position_before = self._get_position_size(symbol)
                            logger.warning(f"⚠️ [FILL-FAILED] Reducing to ${current_usd:.2f} (attempt {attempt + 2}/{max_retries + 1})")
                            continue

                        return {
                            'success': False,
                            'error': 'Order accepted but not filled - margin likely insufficient',
                            'action': 'BUY' if side == 'LONG' else 'SELL',
                            'symbol': symbol
                        }
                else:
                    return {
                        'success': False,
                        'error': f"Order rejected: {result}",
                        'action': 'BUY' if side == 'LONG' else 'SELL',
                        'symbol': symbol
                    }

            except Exception as e:
                logger.error(f"Order error for {symbol}: {e}")
                if attempt < max_retries:
                    current_usd *= 0.5
                    current_size = self._calculate_order_size(symbol, current_usd)
                    if not current_size:
                        break
                    logger.warning(f"⚠️ [ERROR-RETRY] Reducing to ${current_usd:.2f} (attempt {attempt + 2}/{max_retries + 1})")
                    continue

                return {
                    'success': False,
                    'error': str(e),
                    'action': 'BUY' if side == 'LONG' else 'SELL',
                    'symbol': symbol
                }

        # All retries exhausted
        return {
            'success': False,
            'error': 'Failed after all retry attempts',
            'action': 'BUY' if side == 'LONG' else 'SELL',
            'symbol': symbol
        }

    async def _close_position(self, symbol: str, reason: str) -> Dict:
        """
        Close an existing position

        Args:
            symbol: Base symbol
            reason: Close reason

        Returns:
            Execution result
        """
        full_symbol = self._get_full_symbol(symbol)

        # Find position
        positions = self.fetcher.fetch_positions()
        position = None
        for pos in positions:
            if pos.get('symbol') == symbol:
                position = pos
                break

        if not position:
            return {
                'success': False,
                'error': f'No position found for {symbol}',
                'action': 'CLOSE',
                'symbol': symbol
            }

        size = Decimal(str(position['size']))
        side = position['side']
        entry_price = position['entry_price']

        # Get current price
        bbo = self.fetcher.fetch_bbo(symbol)
        exit_price = bbo.get('mid_price', 0) if bbo else 0

        # Calculate P&L
        if side == 'LONG':
            pnl = (exit_price - entry_price) * float(size)
        else:
            pnl = (entry_price - exit_price) * float(size)

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would CLOSE {side} {size} {symbol} @ ~${exit_price:.4f} (P&L: ${pnl:.2f})")
            # Track in trade tracker
            order_id = self.tracker.get_order_id_for_symbol(symbol)
            if order_id:
                self.tracker.log_exit(order_id, exit_price, reason, fees=0)
            return {
                'success': True,
                'action': 'CLOSE',
                'symbol': symbol,
                'size': float(size),
                'price': exit_price,
                'pnl': pnl,
                'dry_run': True
            }

        try:
            # Place closing order (opposite side)
            order = self.Order(
                market=full_symbol,
                order_type=self.OrderType.Market,
                order_side=self.OrderSide.Sell if side == 'LONG' else self.OrderSide.Buy,
                size=size,
            )

            result = self.client.api_client.submit_order(order)

            if result.get('status') in ['NEW', 'FILLED']:
                logger.info(f"Closed {side} {size} {symbol} @ ~${exit_price:.4f} (P&L: ${pnl:.2f})")

                # Track in trade tracker
                order_id = self.tracker.get_order_id_for_symbol(symbol)
                if order_id:
                    self.tracker.log_exit(order_id, exit_price, reason, fees=0)

                return {
                    'success': True,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'size': float(size),
                    'price': exit_price,
                    'pnl': pnl,
                    'order_id': result.get('id')
                }
            else:
                return {
                    'success': False,
                    'error': f"Close order rejected: {result}",
                    'action': 'CLOSE',
                    'symbol': symbol
                }

        except Exception as e:
            logger.error(f"Close order error for {symbol}: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'CLOSE',
                'symbol': symbol
            }

    async def close_all_positions(self, reason: str = "Manual close all") -> List[Dict]:
        """
        Close all open positions

        Returns:
            List of close results
        """
        positions = self.fetcher.fetch_positions()
        results = []

        for pos in positions:
            symbol = pos.get('symbol')
            if symbol:
                result = await self._close_position(symbol, reason)
                results.append(result)

        return results
