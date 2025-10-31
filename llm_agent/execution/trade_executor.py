"""
Trade Executor
Executes LLM trading decisions using existing Pacifica infrastructure

Integrates with:
- PacificaAPI from pacifica_bot.py (order placement)
- RiskManager from risk_manager.py (position sizing)
- TradeTracker from trade_tracker.py (trade logging)

Usage:
    executor = TradeExecutor(
        pacifica_api=api,
        risk_manager=risk_mgr,
        trade_tracker=tracker,
        dry_run=True
    )

    result = executor.execute_decision(decision)
"""

import logging
import sys
import os
import requests
from typing import Optional, Dict
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# Add parent directory to path to import existing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Execute LLM trading decisions with risk management"""

    def __init__(
        self,
        pacifica_sdk,  # PacificaSDK instance
        trade_tracker,  # TradeTracker instance
        dry_run: bool = False,
        default_position_size: float = 30.0,  # USD per trade
        max_positions: int = 3
    ):
        """
        Initialize trade executor

        Args:
            pacifica_sdk: PacificaSDK instance for order placement
            trade_tracker: TradeTracker instance for logging
            dry_run: If True, don't actually place orders (default: False)
            default_position_size: Default position size in USD (default: $30)
            max_positions: Max open positions (default: 3)
        """
        self.sdk = pacifica_sdk
        self.tracker = trade_tracker
        self.dry_run = dry_run
        self.default_position_size = default_position_size
        self.max_positions = max_positions

        # Get account address from SDK for position fetching
        self.account_address = pacifica_sdk.account_address

        mode = "DRY-RUN" if dry_run else "LIVE"
        logger.info(f"✅ TradeExecutor initialized ({mode} mode, ${default_position_size}/trade)")

    def _fetch_positions_from_api(self):
        """
        Fetch current open positions directly from Pacifica API

        Returns:
            List of position dicts with keys: symbol, side, quantity, entry_price
        """
        try:
            response = requests.get(
                "https://api.pacifica.fi/api/v1/positions",
                params={"account": self.account_address},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success") and result.get("data"):
                    positions = []
                    for pos in result["data"]:
                        positions.append({
                            "symbol": pos["symbol"],
                            "side": "LONG" if pos["side"] == "bid" else "SHORT",
                            "quantity": float(pos["amount"]),
                            "entry_price": float(pos["entry_price"])
                        })
                    return positions

            logger.warning("Failed to fetch positions from Pacifica API")
            return []

        except Exception as e:
            logger.error(f"Error fetching positions from API: {e}")
            return []

    def execute_decision(self, decision: Dict) -> Dict:
        """
        Execute LLM trading decision

        Args:
            decision: Dict with keys: action, symbol, reason

        Returns:
            Dict with execution result:
                - success: bool
                - action: str
                - symbol: str
                - order_id: Optional[str]
                - filled_size: Optional[float]
                - filled_price: Optional[float]
                - error: Optional[str]
        """
        action = decision.get("action")
        symbol = decision.get("symbol")
        reason = decision.get("reason", "")

        logger.info(f"Executing decision: {action} {symbol or ''}")
        logger.info(f"Reason: {reason[:100]}...")

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
            return self._close_position(symbol, reason)

        # Handle BUY/SELL
        if action in ["BUY", "SELL"]:
            return self._open_position(action, symbol, reason)

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

    def _open_position(self, action: str, symbol: str, reason: str) -> Dict:
        """
        Open new position (BUY=LONG, SELL=SHORT)

        Args:
            action: BUY or SELL
            symbol: Market symbol
            reason: LLM reasoning

        Returns:
            Execution result dict
        """
        side = "LONG" if action == "BUY" else "SHORT"  # For logging
        sdk_side = "bid" if action == "BUY" else "ask"  # For SDK

        logger.info(f"Opening {side} position in {symbol} (${self.default_position_size})")

        # Get current price from Pacifica orderbook
        try:
            response = requests.get(f"{self.sdk.base_url}/book?symbol={symbol}")
            result = response.json()

            if not result.get("success") or not result.get("data"):
                raise Exception("Failed to get orderbook from API")

            book = result["data"]
            # Get mid price from best bid/ask
            if book.get("l") and len(book["l"]) > 0 and len(book["l"][0]) > 0:
                best_bid = float(book["l"][0][0]["p"])
                best_ask = float(book["l"][1][0]["p"]) if len(book["l"]) > 1 and len(book["l"][1]) > 0 else best_bid
                current_price = (best_bid + best_ask) / 2
            else:
                raise Exception("Empty orderbook")

            logger.info(f"Current price: ${current_price:.2f}")

            # Calculate position size (use default for now)
            position_size_usd = self.default_position_size

            # Get lot size from config (imported at top of file)
            from config import PacificaConfig
            lot_size = PacificaConfig.LOT_SIZES.get(symbol, 0.01)  # Default to 0.01 if not in config

            # Calculate quantity and round to lot size using Decimal for precision
            quantity_raw = Decimal(str(position_size_usd)) / Decimal(str(current_price))
            lot_size_decimal = Decimal(str(lot_size))

            # Round down to nearest lot size multiple
            quantity = float((quantity_raw // lot_size_decimal) * lot_size_decimal)

            logger.info(f"Position: ${position_size_usd:.2f} @ ${current_price:.2f} = {quantity:.4f} {symbol} (lot size: {lot_size})")

        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return {
                "success": False,
                "action": action,
                "symbol": symbol,
                "order_id": None,
                "filled_size": None,
                "filled_price": None,
                "error": f"Position sizing failed: {e}"
            }

        # Dry-run mode
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would place {side} market order: {quantity:.4f} {symbol}")

            # Log simulated trade
            self.tracker.log_entry(
                order_id=None,
                symbol=symbol,
                side=side,
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
            logger.info(f"[LIVE] Placing {side} market order: {quantity:.4f} {symbol}")

            order_result = self.sdk.create_market_order(
                symbol=symbol,
                side=sdk_side,
                amount=str(quantity)
            )

            if not order_result or not order_result.get("success"):
                raise Exception(f"Order failed: {order_result}")

            order_id = order_result.get("order_id")
            filled_size = order_result.get("filled_size", quantity)
            filled_price = order_result.get("filled_price", current_price)

            logger.info(f"✅ Order filled: {filled_size:.4f} {symbol} @ ${filled_price:.2f}")

            # Log trade
            self.tracker.log_entry(
                order_id=order_id,
                symbol=symbol,
                side=side,
                size=filled_size,
                entry_price=filled_price,
                notes=reason
            )

            return {
                "success": True,
                "action": action,
                "symbol": symbol,
                "order_id": order_id,
                "filled_size": filled_size,
                "filled_price": filled_price,
                "error": None
            }

        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            return {
                "success": False,
                "action": action,
                "symbol": symbol,
                "order_id": None,
                "filled_size": None,
                "filled_price": None,
                "error": f"Order failed: {e}"
            }

    def _close_position(self, symbol: str, reason: str) -> Dict:
        """
        Close existing position

        Args:
            symbol: Market symbol
            reason: LLM reasoning

        Returns:
            Execution result dict
        """
        logger.info(f"Closing position in {symbol}")

        # Get current position from Pacifica API (not TradeTracker, which may be out of sync)
        try:
            positions = self._fetch_positions_from_api()
            position = next((p for p in positions if p.get("symbol") == symbol), None)

            if not position:
                raise Exception(f"No open position found for {symbol}")

            # Get opposite side for closing
            current_side = position.get("side")
            close_side = "SHORT" if current_side == "LONG" else "LONG"
            quantity = position.get("quantity")

            logger.info(f"Closing {current_side} position: {quantity:.4f} {symbol}")

        except Exception as e:
            logger.error(f"Failed to get position info: {e}")
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "order_id": None,
                "filled_size": None,
                "filled_price": None,
                "error": f"Position lookup failed: {e}"
            }

        # Dry-run mode
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would close {current_side} position: {quantity:.4f} {symbol}")

            # Mark position as closed (DRY-RUN - skip logging exit for now)
            pass

            return {
                "success": True,
                "action": "CLOSE",
                "symbol": symbol,
                "order_id": "DRY_RUN_CLOSE",
                "filled_size": quantity,
                "filled_price": None,
                "error": None
            }

        # LIVE mode - close position
        try:
            logger.info(f"[LIVE] Closing {current_side} position: {quantity:.4f} {symbol}")

            order_result = self.sdk.close_position(symbol=symbol)

            if not order_result or not order_result.get("success"):
                raise Exception(f"Close order failed: {order_result}")

            order_id = order_result.get("order_id")
            filled_size = order_result.get("filled_size", quantity)
            filled_price = order_result.get("filled_price")

            if filled_price:
                logger.info(f"✅ Position closed: {filled_size:.4f} {symbol} @ ${filled_price:.2f}")
            else:
                logger.info(f"✅ Position closed: {filled_size:.4f} {symbol}")

            # Mark position as closed
            if order_id:
                self.tracker.log_exit(
                    order_id=order_id,
                    exit_price=filled_price,
                    exit_reason=reason
                )

            return {
                "success": True,
                "action": "CLOSE",
                "symbol": symbol,
                "order_id": order_id,
                "filled_size": filled_size,
                "filled_price": filled_price,
                "error": None
            }

        except Exception as e:
            logger.error(f"Close order failed: {e}")
            return {
                "success": False,
                "action": "CLOSE",
                "symbol": symbol,
                "order_id": None,
                "filled_size": None,
                "filled_price": None,
                "error": f"Close failed: {e}"
            }
