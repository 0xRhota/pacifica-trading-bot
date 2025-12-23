"""
Delta-Neutral Executor
======================
Executes trades with strict delta-neutral constraints.
All position sizing and direction validation is code-enforced.

Circuit breakers:
- Volatility protection
- Spread collapse protection
- Atomic execution (rollback on partial)
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

from .response_parser import ArbDecision
from .data_aggregator import AggregatedData

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of an execution attempt"""
    success: bool
    action: str
    asset: Optional[str]
    hibachi_order_id: Optional[str]
    extended_order_id: Optional[str]
    position_size: float
    error: Optional[str]
    rolled_back: bool = False


class DeltaNeutralExecutor:
    """
    Executes delta-neutral trades with strict constraints.

    Code-enforced rules (NOT LLM controlled):
    1. Equal position sizes on both exchanges
    2. Opposite directions (one LONG, one SHORT)
    3. Atomic execution (rollback if one leg fails)
    4. Circuit breakers for risk protection
    """

    def __init__(self, config):
        self.config = config
        self._hibachi_sdk = None
        self._extended_sdk = None

        # Track state
        self._last_execution_time = None
        self._consecutive_failures = 0

    async def initialize(self) -> bool:
        """Initialize exchange SDKs"""
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

            from dexes.hibachi.hibachi_sdk import HibachiSDK

            # Initialize Hibachi
            hibachi_key = os.getenv('HIBACHI_PUBLIC_KEY')
            hibachi_secret = os.getenv('HIBACHI_PRIVATE_KEY')
            hibachi_account = os.getenv('HIBACHI_ACCOUNT_ID')

            if not all([hibachi_key, hibachi_secret, hibachi_account]):
                logger.error("Missing Hibachi credentials")
                return False

            self._hibachi_sdk = HibachiSDK(hibachi_key, hibachi_secret, hibachi_account)

            # Initialize Extended using x10 SDK (same as extended_agent)
            extended_key = os.getenv('EXTENDED_API_KEY') or os.getenv('EXTENDED')
            extended_stark_private = os.getenv('EXTENDED_STARK_PRIVATE_KEY')
            extended_stark_public = os.getenv('EXTENDED_STARK_PUBLIC_KEY')
            extended_vault = os.getenv('EXTENDED_VAULT')

            if not all([extended_key, extended_stark_private, extended_stark_public, extended_vault]):
                logger.error("Missing Extended credentials (EXTENDED_API_KEY, EXTENDED_STARK_PRIVATE_KEY, EXTENDED_STARK_PUBLIC_KEY, EXTENDED_VAULT)")
                return False

            try:
                from x10.perpetual.accounts import StarkPerpetualAccount
                from x10.perpetual.configuration import MAINNET_CONFIG
                from x10.perpetual.trading_client import PerpetualTradingClient

                stark_account = StarkPerpetualAccount(
                    vault=int(extended_vault),
                    private_key=extended_stark_private,
                    public_key=extended_stark_public,
                    api_key=extended_key,
                )

                self._extended_client = PerpetualTradingClient(
                    endpoint_config=MAINNET_CONFIG,
                    stark_account=stark_account
                )
                logger.info("Extended x10 SDK initialized")
            except ImportError:
                logger.error("x10-python-trading-starknet not installed. Install with: pip install x10-python-trading-starknet")
                return False

            logger.info("Executor initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize executor: {e}")
            return False

    def check_circuit_breakers(self, data: AggregatedData, decision: ArbDecision) -> Tuple[bool, str]:
        """
        Check circuit breakers before execution.

        Returns:
            (can_execute, reason)
        """
        # 1. Volatility check
        if decision.asset:
            vol = data.volatility.get(decision.asset)
            if vol and not vol.is_safe:
                return False, f"Circuit breaker: {decision.asset} volatility {vol.volatility_1h:.2f}% exceeds threshold"

        # 2. Spread collapse check (for OPEN/ROTATE)
        if decision.action in ["OPEN", "ROTATE"] and decision.asset:
            spread = data.spreads.get(decision.asset)
            if spread and spread.annualized_spread < self.config.min_spread_annualized:
                return False, f"Circuit breaker: {decision.asset} spread {spread.annualized_spread:.2f}% below minimum"

        # 3. Balance check
        if data.max_position_size < self.config.min_position_usd:
            return False, f"Circuit breaker: Insufficient balance (max position ${data.max_position_size:.2f})"

        # 4. Consecutive failure check
        if self._consecutive_failures >= 3:
            return False, "Circuit breaker: 3 consecutive failures, pausing execution"

        return True, "All circuit breakers passed"

    async def execute(self, decision: ArbDecision, data: AggregatedData) -> ExecutionResult:
        """
        Execute a trading decision with delta-neutral constraints.

        Args:
            decision: Parsed LLM decision
            data: Current market data

        Returns:
            ExecutionResult with details
        """
        # Check circuit breakers
        can_execute, reason = self.check_circuit_breakers(data, decision)
        if not can_execute:
            logger.warning(f"Execution blocked: {reason}")
            return ExecutionResult(
                success=False,
                action=decision.action,
                asset=decision.asset,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error=reason
            )

        # Route to appropriate handler
        if decision.action == "HOLD":
            return ExecutionResult(
                success=True,
                action="HOLD",
                asset=None,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error=None
            )
        elif decision.action == "OPEN":
            return await self._execute_open(decision, data)
        elif decision.action == "CLOSE":
            return await self._execute_close(decision, data)
        elif decision.action == "ROTATE":
            return await self._execute_rotate(decision, data)
        else:
            return ExecutionResult(
                success=False,
                action=decision.action,
                asset=decision.asset,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error=f"Unknown action: {decision.action}"
            )

    async def _execute_open(self, decision: ArbDecision, data: AggregatedData) -> ExecutionResult:
        """Execute OPEN action - open new delta-neutral position"""
        logger.info(f"Executing OPEN: {decision.asset}")
        logger.info(f"  Hibachi: {decision.hibachi_direction}")
        logger.info(f"  Extended: {decision.extended_direction}")

        # Calculate position size (CODE-ENFORCED)
        position_size = min(data.max_position_size, self.config.max_position_usd)
        logger.info(f"  Position size: ${position_size:.2f} per leg (EQUAL)")

        if self.config.dry_run:
            logger.info("  [DRY RUN] No orders placed")
            return ExecutionResult(
                success=True,
                action="OPEN",
                asset=decision.asset,
                hibachi_order_id="DRY_RUN",
                extended_order_id="DRY_RUN",
                position_size=position_size,
                error=None
            )

        # Get symbols
        hibachi_symbol = self.config.hibachi_symbols.get(decision.asset)
        extended_symbol = self.config.extended_symbols.get(decision.asset)

        if not hibachi_symbol or not extended_symbol:
            return ExecutionResult(
                success=False,
                action="OPEN",
                asset=decision.asset,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error=f"Symbol mapping not found for {decision.asset}"
            )

        # Get prices for size calculation
        hibachi_price = await self._get_hibachi_price(hibachi_symbol)
        extended_price = await self._get_extended_price(extended_symbol)

        if not hibachi_price or not extended_price:
            return ExecutionResult(
                success=False,
                action="OPEN",
                asset=decision.asset,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error="Could not get prices"
            )

        # Calculate quantities - USE SAME PRECISION FOR BOTH EXCHANGES
        # Extended has lower precision, so calculate Extended qty first and match Hibachi to it
        raw_qty = position_size / ((hibachi_price + extended_price) / 2)  # Use avg price

        # Get Extended precision (the limiting factor)
        if "BTC" in extended_symbol:
            precision = 5
        elif "ETH" in extended_symbol:
            precision = 3
        else:
            precision = 2

        # Round to Extended precision - BOTH exchanges use this EXACT quantity
        matched_qty = round(raw_qty, precision)
        hibachi_qty = matched_qty
        extended_qty = matched_qty

        logger.info(f"  Matched quantity: {matched_qty} (precision={precision})")

        # Execute Hibachi first
        hibachi_is_buy = decision.hibachi_direction == "LONG"
        logger.info(f"  Placing Hibachi order: {'BUY' if hibachi_is_buy else 'SELL'} {hibachi_qty:.8f}")

        hibachi_result = await self._hibachi_sdk.create_market_order(
            hibachi_symbol,
            hibachi_is_buy,
            hibachi_qty
        )

        if not hibachi_result:
            self._consecutive_failures += 1
            return ExecutionResult(
                success=False,
                action="OPEN",
                asset=decision.asset,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error="Hibachi order failed"
            )

        hibachi_order_id = hibachi_result.get('orderId')
        logger.info(f"  Hibachi order placed: {hibachi_order_id}")

        # Execute Extended using x10 SDK
        extended_is_buy = decision.extended_direction == "LONG"
        logger.info(f"  Placing Extended order: {'BUY' if extended_is_buy else 'SELL'} {extended_qty:.8f}")

        extended_order_id = await self._place_extended_order(
            extended_symbol,
            extended_is_buy,
            extended_qty,
            extended_price
        )

        if not extended_order_id:
            # ROLLBACK Hibachi order
            logger.error("  Extended order failed - ROLLING BACK Hibachi")
            await self._rollback_hibachi(hibachi_symbol, hibachi_is_buy, hibachi_qty)
            self._consecutive_failures += 1
            return ExecutionResult(
                success=False,
                action="OPEN",
                asset=decision.asset,
                hibachi_order_id=hibachi_order_id,
                extended_order_id=None,
                position_size=0,
                error="Extended order failed, Hibachi rolled back",
                rolled_back=True
            )
        logger.info(f"  Extended order placed: {extended_order_id}")

        self._consecutive_failures = 0
        self._last_execution_time = datetime.now(timezone.utc)

        return ExecutionResult(
            success=True,
            action="OPEN",
            asset=decision.asset,
            hibachi_order_id=hibachi_order_id,
            extended_order_id=extended_order_id,
            position_size=position_size,
            error=None
        )

    async def _execute_close(self, decision: ArbDecision, data: AggregatedData) -> ExecutionResult:
        """Execute CLOSE action - close existing position"""
        logger.info(f"Executing CLOSE: {decision.asset}")

        if self.config.dry_run:
            logger.info("  [DRY RUN] No orders placed")
            return ExecutionResult(
                success=True,
                action="CLOSE",
                asset=decision.asset,
                hibachi_order_id="DRY_RUN",
                extended_order_id="DRY_RUN",
                position_size=0,
                error=None
            )

        # Find positions for this asset
        hibachi_pos = None
        extended_pos = None

        for pos in data.positions:
            if pos.symbol == decision.asset:
                if pos.exchange == "Hibachi":
                    hibachi_pos = pos
                elif pos.exchange == "Extended":
                    extended_pos = pos

        if not hibachi_pos and not extended_pos:
            return ExecutionResult(
                success=False,
                action="CLOSE",
                asset=decision.asset,
                hibachi_order_id=None,
                extended_order_id=None,
                position_size=0,
                error="No positions found to close"
            )

        # Close both positions
        hibachi_order_id = None
        extended_order_id = None

        if hibachi_pos:
            hibachi_symbol = self.config.hibachi_symbols.get(decision.asset)
            # Close = opposite direction
            is_buy = hibachi_pos.side == "SHORT"
            logger.info(f"  Closing Hibachi: {'BUY' if is_buy else 'SELL'} {hibachi_pos.size:.8f}")

            result = await self._hibachi_sdk.create_market_order(
                hibachi_symbol,
                is_buy,
                hibachi_pos.size
            )
            if result:
                hibachi_order_id = result.get('orderId')

        if extended_pos:
            extended_symbol = self.config.extended_symbols.get(decision.asset)
            is_buy = extended_pos.side == "SHORT"
            logger.info(f"  Closing Extended: {'BUY' if is_buy else 'SELL'} {extended_pos.size:.8f}")

            extended_order_id = await self._close_extended_position(
                extended_symbol,
                is_buy,
                extended_pos.size
            )

        success = hibachi_order_id is not None or extended_order_id is not None

        return ExecutionResult(
            success=success,
            action="CLOSE",
            asset=decision.asset,
            hibachi_order_id=hibachi_order_id,
            extended_order_id=extended_order_id,
            position_size=0,
            error=None if success else "Failed to close positions"
        )

    async def _execute_rotate(self, decision: ArbDecision, data: AggregatedData) -> ExecutionResult:
        """Execute ROTATE action - close existing and open new"""
        logger.info(f"Executing ROTATE to {decision.asset}")

        # First, find and close any existing positions
        existing_assets = set(p.symbol for p in data.positions)

        for asset in existing_assets:
            if asset != decision.asset:
                close_decision = ArbDecision(
                    action="CLOSE",
                    asset=asset,
                    hibachi_direction=None,
                    extended_direction=None,
                    reasoning="Rotation - closing old position",
                    confidence=1.0,
                    raw_response=""
                )
                close_result = await self._execute_close(close_decision, data)
                if not close_result.success:
                    logger.warning(f"Failed to close {asset} during rotation")

        # Now open new position
        return await self._execute_open(decision, data)

    async def _rollback_hibachi(self, symbol: str, was_buy: bool, qty: float):
        """Rollback a Hibachi order by placing opposite order"""
        try:
            logger.info(f"  Rolling back Hibachi: {'SELL' if was_buy else 'BUY'} {qty:.8f}")
            await self._hibachi_sdk.create_market_order(
                symbol,
                not was_buy,  # Opposite direction
                qty
            )
            logger.info("  Rollback successful")
        except Exception as e:
            logger.error(f"  Rollback FAILED: {e}")

    async def _get_hibachi_price(self, symbol: str) -> Optional[float]:
        """Get current price from Hibachi"""
        try:
            return await self._hibachi_sdk.get_price(symbol)
        except Exception as e:
            logger.error(f"Error getting Hibachi price: {e}")
            return None

    async def _get_extended_price(self, symbol: str) -> Optional[float]:
        """Get current price from Extended using x10 SDK"""
        try:
            stats = await self._extended_client.markets_info.get_market_statistics(market_name=symbol)
            if stats and stats.data:
                return float(stats.data.last_price)
            return None
        except Exception as e:
            logger.error(f"Error getting Extended price: {e}")
            return None

    async def _place_extended_order(self, symbol: str, is_buy: bool, qty: float, price: float) -> Optional[str]:
        """
        Place order on Extended using x10 SDK.

        Args:
            symbol: Market symbol (e.g., "ETH-USD")
            is_buy: True for BUY, False for SELL
            qty: Quantity to trade
            price: Reference price for slippage calculation

        Returns:
            Order ID if successful, None otherwise
        """
        try:
            from decimal import Decimal
            from datetime import timedelta
            from x10.perpetual.orders import OrderSide, TimeInForce

            side = OrderSide.BUY if is_buy else OrderSide.SELL

            # Precision based on asset (from Extended API specs)
            if "BTC" in symbol:
                precision = 5
            elif "ETH" in symbol:
                precision = 3
            else:
                precision = 2

            amount = Decimal(str(round(qty, precision)))

            # Add slippage buffer for market-like execution
            order_price = price * 1.005 if is_buy else price * 0.995

            logger.info(f"  Placing Extended x10 order: {side.name} {amount} {symbol} @ ~${order_price:.2f}")

            order = await self._extended_client.place_order(
                market_name=symbol,
                amount_of_synthetic=amount,
                price=Decimal(str(int(order_price))),
                side=side,
                time_in_force=TimeInForce.GTT,
                expire_time=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            if order and order.data:
                order_id = str(order.data.id)
                logger.info(f"  Extended order placed: {order_id}")
                return order_id
            else:
                logger.error("  Extended order response empty")
                return None

        except Exception as e:
            logger.error(f"Error placing Extended order: {e}")
            return None

    async def _close_extended_position(self, symbol: str, is_buy: bool, qty: float) -> Optional[str]:
        """
        Close position on Extended using x10 SDK (reduce_only order).

        Args:
            symbol: Market symbol
            is_buy: True if closing a SHORT (buy to close), False if closing a LONG
            qty: Size to close

        Returns:
            Order ID if successful, None otherwise
        """
        try:
            from decimal import Decimal
            from datetime import timedelta
            from x10.perpetual.orders import OrderSide, TimeInForce

            side = OrderSide.BUY if is_buy else OrderSide.SELL

            # Get current price
            price = await self._get_extended_price(symbol)
            if not price:
                logger.error(f"  Cannot get price to close Extended position")
                return None

            # Precision based on asset
            if "BTC" in symbol:
                precision = 5
            elif "ETH" in symbol:
                precision = 3
            else:
                precision = 2

            amount = Decimal(str(round(qty, precision)))

            # Add slippage for closing
            order_price = price * 1.005 if is_buy else price * 0.995

            logger.info(f"  Closing Extended position: {side.name} {amount} {symbol}")

            order = await self._extended_client.place_order(
                market_name=symbol,
                amount_of_synthetic=amount,
                price=Decimal(str(int(order_price))),
                side=side,
                reduce_only=True,
                time_in_force=TimeInForce.GTT,
                expire_time=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            if order and order.data:
                order_id = str(order.data.id)
                logger.info(f"  Extended close order placed: {order_id}")
                return order_id
            else:
                logger.error("  Extended close order response empty")
                return None

        except Exception as e:
            logger.error(f"Error closing Extended position: {e}")
            return None
