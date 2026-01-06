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
from utils.cambrian_risk_engine import CambrianRiskEngine, RiskAssessment

logger = logging.getLogger(__name__)


class HibachiTradeExecutor:
    """
    Execute LLM trading decisions for Hibachi DEX

    Args:
        hibachi_sdk: HibachiSDK instance for order placement
        trade_tracker: TradeTracker instance for logging
        dry_run: If True, don't actually place orders (default: False)
        default_position_size: Default position size in USD (default: $10 to offset fees)
        max_positions: Max open positions (default: 10)
    """

    def __init__(
        self,
        hibachi_sdk,  # HibachiSDK instance
        trade_tracker: TradeTracker,
        dry_run: bool = False,
        default_position_size: float = 10.0,  # $10 per trade - larger to offset fees
        max_positions: int = 5,  # Reduced from 10 to force selectivity
        min_confidence: float = 0.7,  # v7: Raised from 0.6 (Qwen recommendation)
        max_position_age_minutes: int = 240,  # 4 hours (same as Lighter)
        cambrian_api_key: str = None  # For risk engine
    ):
        self.sdk = hibachi_sdk
        self.tracker = trade_tracker
        self.dry_run = dry_run
        self.default_position_size = default_position_size
        self.max_positions = max_positions
        self.min_confidence = min_confidence
        self.max_position_age_minutes = max_position_age_minutes

        # Hibachi fee rate (taker fee ~0.035% per trade)
        # Round-trip = entry + exit = ~0.07% total
        self.fee_rate = 0.00035  # 0.035% per transaction

        # Initialize Cambrian Risk Engine
        self.risk_engine = None
        if cambrian_api_key:
            try:
                self.risk_engine = CambrianRiskEngine(cambrian_api_key)
                logger.info("✅ Cambrian Risk Engine enabled")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize risk engine: {e}")

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
                        # Handle both datetime and string timestamps
                        if isinstance(open_time, str):
                            try:
                                open_time = datetime.fromisoformat(open_time)
                            except ValueError:
                                continue
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

        # ═══════════════════════════════════════════════════════════════
        # FEE FILTER - Reject low-confidence trades (v2 fee optimization)
        # Round-trip fees = 0.09% → need >0.09% edge to break even
        # Low confidence setups won't overcome fee drag
        # ═══════════════════════════════════════════════════════════════
        confidence = decision.get('confidence', 0.5)
        if action in ['LONG', 'SHORT'] and confidence < self.min_confidence:
            logger.info(f"💸 [FEE-FILTER] Skipping {action} {symbol} - confidence {confidence:.2f} < {self.min_confidence} (fees would eat edge)")
            return {
                'success': False,
                'action': action,
                'symbol': symbol,
                'error': f'Confidence {confidence:.2f} below min {self.min_confidence} - fee filter',
                'filtered_by': 'fee_filter'
            }

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

            # DYNAMIC LEVERAGE SYSTEM (v6 - Aggressive sizing 2025-12-05)
            # Key insight: Perps allow notional > account balance
            # Higher confidence = higher leverage = MUCH bigger bets on strong setups
            # Extended bot uses $500-600 positions - we should too
            confidence = decision.get('confidence', 0.5) if decision else 0.5
            account_balance = await self._fetch_account_balance()

            # Aggressive leverage tiers (v6 - based on Lighter analysis)
            # Note: 0.8+ confidence underperforms on Lighter - cap leverage there
            # | Confidence | Leverage | Base% | Example ($70 acct) |
            # |------------|----------|-------|-------------------|
            # | <0.6       | REJECT   | -     | Filtered          |
            # | 0.6-0.7    | 4x       | 50%   | $140 notional     |
            # | 0.7-0.8    | 6x       | 60%   | $252 notional     |
            # | 0.8-0.9    | 5x       | 50%   | $175 notional     | ← Reduced! Overconf trap
            # | 0.9+       | 4x       | 40%   | $112 notional     | ← Most reduced!

            if account_balance and account_balance > 1.0:
                # Confidence-based leverage scaling (min confidence 0.6 enforced by fee filter)
                # NOTE: Based on Lighter data, 0.8+ confidence UNDERPERFORMS
                # We scale DOWN leverage for highest confidence (overconfidence trap)
                if confidence < 0.7:
                    leverage = 4.0   # Decent setup - solid bet
                    base_pct = 0.50  # 50% of account
                elif confidence < 0.8:
                    leverage = 6.0   # Sweet spot! Best WR on Lighter
                    base_pct = 0.60  # 60% of account - max aggression
                elif confidence < 0.9:
                    leverage = 5.0   # High conf but risky - dial back
                    base_pct = 0.50  # 50% - more cautious
                else:
                    leverage = 4.0   # Very high conf = overconfidence trap
                    base_pct = 0.40  # 40% - be careful here

                position_size_usd = account_balance * base_pct * leverage

                # Minimum $100 notional, maximum $1000 notional per position
                # (Risk engine will block if liquidation risk too high)
                min_size = 100.0
                max_size = 1000.0
                position_size_usd = max(min_size, min(position_size_usd, max_size))

                # Check remaining capacity (don't overextend)
                positions = await self._fetch_open_positions()
                current_positions = len([p for p in positions if float(p.get('quantity', 0)) > 0]) if positions else 0

                if current_positions >= self.max_positions:
                    logger.warning(f"⚠️ Max positions ({self.max_positions}) reached")

                logger.info(
                    f"🚀 Leveraged sizing: ${account_balance:.2f} balance × {leverage:.1f}x | "
                    f"conf={confidence:.2f} → ${position_size_usd:.2f} notional "
                    f"(margin ~${position_size_usd/leverage:.2f})"
                )
            else:
                # Fallback to minimum leveraged size
                position_size_usd = 50.0  # Minimum $50 notional
                leverage = 2.0  # Default leverage for fallback
                if account_balance is None:
                    logger.warning("Could not fetch balance - using minimum leveraged size ($50)")
                else:
                    logger.warning(f"Balance too small (${account_balance:.2f}) - using minimum leveraged size ($50)")

            # ═══════════════════════════════════════════════════════════════
            # CAMBRIAN RISK ENGINE CHECK
            # Monte Carlo simulation to assess liquidation probability
            # ═══════════════════════════════════════════════════════════════
            risk_assessment = None
            if self.risk_engine:
                try:
                    direction = "long" if action == "LONG" else "short"
                    risk_assessment = self.risk_engine.assess_risk(
                        symbol=symbol,
                        entry_price=price,
                        leverage=leverage,
                        direction=direction,
                        risk_horizon="1d"  # 1 day horizon for scalping
                    )

                    if risk_assessment:
                        # Log detailed assessment
                        self.risk_engine.log_assessment(risk_assessment)

                        # Check if trade should be blocked
                        should_block, block_reason = self.risk_engine.should_block_trade(risk_assessment)

                        if should_block:
                            logger.warning(f"🚨 TRADE BLOCKED BY RISK ENGINE: {block_reason}")
                            logger.warning(f"   {risk_assessment.to_log_string()}")
                            return {
                                'success': False,
                                'action': action,
                                'symbol': symbol,
                                'error': f'Risk too high: {block_reason}',
                                'risk_assessment': {
                                    'risk_pct': risk_assessment.risk_probability * 100,
                                    'liq_price': risk_assessment.liquidation_price,
                                    'sigmas_away': risk_assessment.sigmas_away
                                }
                            }

                        # Apply position size multiplier based on risk
                        risk_multiplier = self.risk_engine.get_position_size_multiplier(risk_assessment)
                        if risk_multiplier < 1.0:
                            original_size = position_size_usd
                            position_size_usd *= risk_multiplier
                            logger.info(
                                f"⚠️ Risk-adjusted size: ${original_size:.2f} × {risk_multiplier:.2f} = ${position_size_usd:.2f} "
                                f"(Risk: {risk_assessment.risk_probability*100:.1f}%)"
                            )
                    else:
                        logger.debug(f"[RISK] No assessment available for {symbol}")

                except Exception as e:
                    logger.warning(f"[RISK] Error during risk check: {e} - proceeding with trade")

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

            # Execute real order with dynamic risk limit retry
            max_retries = 3  # More retries for dynamic sizing
            current_amount = amount
            current_notional = position_size_usd
            import re

            # CRITICAL: Get position BEFORE placing order to verify fill later
            position_before = await self.sdk.get_position_size(symbol)

            for attempt in range(max_retries + 1):
                order = await self.sdk.create_market_order(symbol, is_buy, current_amount)

                # Check for error response (SDK now returns {'error': msg} instead of None)
                if order and isinstance(order, dict) and 'error' in order:
                    error_msg = str(order.get('error', '')).lower()
                    logger.warning(f"⚠️ Order error for {symbol}: {error_msg[:100]}")

                    # Check if this is a retryable risk/margin error
                    is_risk_error = any(kw in error_msg for kw in [
                        'risk', 'limit', 'exceed', 'margin', 'insufficient',
                        'balance', 'collateral', 'equity', 'max', 'position'
                    ])

                    if is_risk_error and attempt < max_retries:
                        # Strategy 1: Get actual available margin from account
                        try:
                            account_info = await self.sdk.get_account_info()
                            if account_info and isinstance(account_info, dict):
                                # Try multiple possible field names
                                available = None
                                for field in ['availableMargin', 'available_margin', 'freeMargin',
                                              'available', 'withdrawable', 'equity', 'balance']:
                                    val = account_info.get(field)
                                    if val is not None:
                                        try:
                                            available = float(val)
                                            if available > 0:
                                                break
                                        except (ValueError, TypeError):
                                            continue

                                if available and available > 10:
                                    # Size to 60% of available (conservative buffer)
                                    new_notional = available * 0.60
                                    if new_notional < current_notional:
                                        current_notional = new_notional
                                        current_amount = current_notional / price
                                        logger.warning(
                                            f"⚠️ [RISK-RETRY] Sizing to 60% of available: "
                                            f"${current_notional:.2f} (attempt {attempt + 2}/{max_retries + 1})"
                                        )
                                        continue
                        except Exception as e:
                            logger.warning(f"Could not get account info: {e}")

                        # Strategy 2: Parse limit from error message
                        numbers = re.findall(r'[\d.]+', error_msg)
                        for num_str in numbers:
                            try:
                                parsed_num = float(num_str)
                                if 10 < parsed_num < current_notional:  # Sanity check
                                    current_notional = parsed_num * 0.85  # 85% of limit
                                    current_amount = current_notional / price
                                    logger.warning(
                                        f"⚠️ [RISK-RETRY] Sizing to 85% of parsed limit: "
                                        f"${current_notional:.2f} (attempt {attempt + 2}/{max_retries + 1})"
                                    )
                                    break
                            except ValueError:
                                continue
                        else:
                            # Strategy 3: Progressive reduction
                            reduction = 0.6 if attempt == 0 else 0.5  # 40% then 50% reduction
                            current_notional *= reduction
                            current_amount = current_notional / price
                            logger.warning(
                                f"⚠️ [RISK-RETRY] Reducing by {int((1-reduction)*100)}%: "
                                f"${current_notional:.2f} (attempt {attempt + 2}/{max_retries + 1})"
                            )
                        continue

                    # Non-retryable error or max retries reached
                    logger.error(f"❌ Order failed for {symbol}: {error_msg[:200]}")
                    return {
                        'success': False,
                        'action': action,
                        'symbol': symbol,
                        'error': order.get('error', 'Order execution failed')
                    }

                # API returned orderId - but this does NOT mean the order filled!
                # The exchange may reject it post-acceptance due to margin issues
                if order and 'orderId' in order:
                    logger.info(f"📝 Order accepted by API: {order.get('orderId')} - verifying fill...")

                    # CRITICAL: Verify the order actually filled by checking position change
                    expected_change = current_amount if is_buy else -current_amount
                    verify_result = await self.sdk.verify_order_fill(
                        symbol=symbol,
                        expected_change=expected_change,
                        position_before=position_before,
                        max_wait_seconds=3.0
                    )

                    if verify_result.get('filled'):
                        # Order actually filled!
                        if attempt > 0:
                            logger.info(f"✅ Order FILLED after {attempt + 1} attempts (adjusted: ${current_notional:.2f})")
                        else:
                            logger.info(f"✅ Order FILLED: {symbol} {action} {current_amount:.6f}")

                        # Record in tracker
                        self.tracker.log_entry(
                            order_id=order.get('orderId'),
                            symbol=symbol,
                            side=action.lower(),
                            entry_price=price,
                            size=current_amount,
                            notes=reason
                        )

                        return {
                            'success': True,
                            'action': action,
                            'symbol': symbol,
                            'price': price,
                            'amount': current_amount,
                            'order': order
                        }
                    else:
                        # Order was accepted but NOT filled - likely margin rejection
                        logger.error(f"❌ Order NOT FILLED for {symbol}: {verify_result.get('error', 'unknown')}")

                        # Treat this as a margin error and retry with smaller size
                        if attempt < max_retries:
                            # Progressive reduction
                            reduction = 0.5  # 50% reduction
                            current_notional *= reduction
                            current_amount = current_notional / price
                            # Update position_before for next attempt
                            position_before = await self.sdk.get_position_size(symbol)
                            logger.warning(
                                f"⚠️ [FILL-FAILED] Reducing size by 50%: "
                                f"${current_notional:.2f} (attempt {attempt + 2}/{max_retries + 1})"
                            )
                            continue

                        # Max retries reached
                        return {
                            'success': False,
                            'action': action,
                            'symbol': symbol,
                            'error': 'Order accepted but not filled - margin likely insufficient'
                        }
                else:
                    # Unexpected response format
                    logger.error(f"❌ Unexpected order response for {symbol}: {order}")
                    return {
                        'success': False,
                        'action': action,
                        'symbol': symbol,
                        'error': f'Unexpected response: {order}'
                    }

            # All retries exhausted
            logger.error(f"❌ Order failed after {max_retries + 1} attempts - risk limit for {symbol}")
            return {
                'success': False,
                'action': action,
                'symbol': symbol,
                'error': 'Risk limit exceeded after retries'
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

                # Get tracker position for PnL with fee estimation
                tracker_pos = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_pos:
                    order_id = tracker_pos.get('order_id')
                    entry_price = tracker_pos.get('entry_price', 0)
                    size = tracker_pos.get('size', 0)
                    # Estimate fees on entry notional * 2 (entry + exit)
                    estimated_fees = (size * entry_price * 2) * self.fee_rate

                    self.tracker.log_exit(
                        order_id=order_id,
                        exit_price=0,  # Don't have real price in dry-run
                        exit_reason=reason,
                        fees=estimated_fees
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

                # Get tracker position for PnL with fee estimation
                tracker_pos = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_pos:
                    price = await self.sdk.get_price(symbol)
                    order_id = tracker_pos.get('order_id')
                    entry_price = tracker_pos.get('entry_price', 0)
                    size = tracker_pos.get('size', 0)

                    # Estimate round-trip fees (entry + exit)
                    # Fee = notional * fee_rate for each leg
                    entry_notional = size * entry_price
                    exit_notional = size * (price if price else entry_price)
                    estimated_fees = (entry_notional + exit_notional) * self.fee_rate

                    self.tracker.log_exit(
                        order_id=order_id,
                        exit_price=price if price else 0,
                        exit_reason=reason,
                        fees=estimated_fees
                    )
                    logger.info(f"   Estimated fees: ${estimated_fees:.4f}")

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
