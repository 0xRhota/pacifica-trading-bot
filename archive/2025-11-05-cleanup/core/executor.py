"""Unified Trade Executor - Works with any DEX adapter"""

import logging
import asyncio
from typing import Dict, Optional
from dexes.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class UnifiedExecutor:
    """Unified trade executor - works with any DEX adapter"""

    # Lighter DEX minimum order sizes (exchange-enforced)
    # Based on old working bot + conservative estimates for new tokens
    LIGHTER_MINIMUMS = {
        'BTC': {'base_units': 0.0001, 'usd': 10.0},
        'ETH': {'base_units': 0.01, 'usd': 10.0},
        'SOL': {'base_units': 0.050, 'usd': 10.0},
        'PENGU': {'base_units': 500, 'usd': 10.0},  # Conservative estimate
        'ZEC': {'base_units': 0.020, 'usd': 10.0},  # Conservative estimate
        'DEFAULT': {'base_units': 0.01, 'usd': 10.0},  # Fallback for unknown tokens
    }

    def __init__(self, adapter: BaseAdapter, logger_instance, dry_run: bool = False,
                 default_position_size: float = 12.0, max_positions: int = 15,
                 reserve_pct: float = 0.15, use_dynamic_sizing: bool = True):
        self.adapter = adapter
        self.logger = logger_instance
        self.dry_run = dry_run
        self.default_position_size = default_position_size  # Kept for backwards compatibility
        self.max_positions = max_positions
        self.reserve_pct = reserve_pct  # Reserve % of account (default 15%)
        self.use_dynamic_sizing = use_dynamic_sizing  # Enable/disable dynamic sizing
    
    async def execute_decision(self, decision: Dict, dry_run: bool = False) -> Dict:
        """Execute a trading decision"""
        action = decision.get("action", "").upper()
        symbol = decision.get("symbol", "")
        reason = decision.get("reason", "")
        confidence = decision.get("confidence", 0.5)
        
        use_dry_run = dry_run or self.dry_run
        
        self.logger.info(f"Executing {action} {symbol}", 
                        component="executor",
                        data={"reason": reason.replace('\n', ' '), "confidence": confidence})
        
        if action == "NOTHING":
            return {"success": True, "action": "NOTHING"}
        
        if action == "CLOSE":
            return await self._close_position(symbol, use_dry_run)
        
        if action in ["BUY", "SELL"]:
            return await self._open_position(action, symbol, confidence, use_dry_run)
        
        return {"success": False, "error": f"Invalid action: {action}"}
    
    async def _open_position(self, action: str, symbol: str, confidence: float, dry_run: bool) -> Dict:
        """Open new position"""
        # Check max positions
        positions = await self.adapter.get_positions()
        if len(positions) >= self.max_positions:
            return {"success": False, "error": f"Max positions ({self.max_positions}) reached"}
        
        # Get balance first for dynamic sizing
        balance = await self.adapter.get_balance()

        # Calculate position size based on approach
        if self.use_dynamic_sizing and balance and balance > 0:
            # APPROACH 1: ADAPTIVE EQUAL-WEIGHT
            # Divide available capital by max positions, then apply confidence multiplier
            available = balance * (1 - self.reserve_pct)
            base_position = available / self.max_positions

            # Confidence multiplier
            if confidence < 0.5:
                multiplier = 0.7
            elif confidence < 0.7:
                multiplier = 1.0
            elif confidence < 0.9:
                multiplier = 1.3
            else:
                multiplier = 1.6

            calculated_size = base_position * multiplier

            # Get exchange minimum for this token
            min_config = self.LIGHTER_MINIMUMS.get(symbol, self.LIGHTER_MINIMUMS['DEFAULT'])

            # Get current price to calculate minimum in USD
            market_data = await self.adapter.get_market_data(symbol)
            if not market_data:
                return {"success": False, "error": f"Could not fetch market data for {symbol}"}
            current_price = market_data.get('price', 0)
            if current_price == 0:
                return {"success": False, "error": f"Invalid price for {symbol}"}

            # Calculate actual minimum USD (max of usd minimum and base_units minimum)
            usd_min = min_config['usd']
            base_units_min_usd = min_config['base_units'] * current_price
            min_size = max(usd_min, base_units_min_usd)

            # Use the larger of calculated size or minimum
            size = max(calculated_size, min_size)

            # Safety: Check if we have enough remaining balance
            positions = await self.adapter.get_positions()
            current_positions = len(positions)
            remaining = available - (current_positions * base_position)  # Rough estimate

            if size > remaining and remaining >= min_size:
                size = remaining  # Use whatever is left if it meets minimum

            # Log position sizing details
            used_minimum = size == min_size
            status = "MIN OVERRIDE" if used_minimum else "CALCULATED"
            self.logger.info(
                f"💰 Position sizing: {symbol} | conf={confidence:.2f} | "
                f"calculated=${calculated_size:.2f} | min=${min_size:.2f} | "
                f"final=${size:.2f} ({size/balance*100:.1f}% of account) [{status}]",
                component="executor"
            )
        else:
            # Fallback to old hardcoded approach if dynamic sizing disabled or no balance
            base_size = self.default_position_size
            if confidence < 0.5:
                size = base_size * 0.8
            elif confidence < 0.7:
                size = base_size * 1.0
            elif confidence < 0.9:
                size = base_size * 1.5
            else:
                size = base_size * 2.0

            if balance and balance > 0:
                size = min(size, balance * 0.9)  # 90% of balance max

            # Get market data for price (for old approach)
            market_data = await self.adapter.get_market_data(symbol)
            if not market_data:
                return {"success": False, "error": f"Could not fetch market data for {symbol}"}
            current_price = market_data.get('price', 0)
            if current_price == 0:
                return {"success": False, "error": f"Invalid price for {symbol}"}
        # else: market_data and current_price already fetched in dynamic sizing path
        
        # Calculate amount in base units
        # For Pacifica: need to use lot sizes
        # For Lighter: adapter handles conversion internally
        adapter_name = self.adapter.get_name()
        if adapter_name == "pacifica":
            # Pacifica: amount is in base units, need to round to lot size
            from config import PacificaConfig
            lot_size = PacificaConfig.LOT_SIZES.get(symbol, 0.01)
            base_units = size / current_price
            # Round to nearest lot size
            amount = round(base_units / lot_size) * lot_size
            if amount < lot_size:
                amount = lot_size  # Minimum is one lot size
        else:
            # Lighter: adapter handles conversion internally
            # Just pass the USD amount, adapter will convert using dynamic decimals
            amount = size / current_price  # This is approximate, adapter will handle precise conversion

            # ✅ PRE-SUBMISSION VALIDATION FOR LIGHTER DEX
            # Validate against exchange minimums BEFORE submitting
            # This prevents infinite retry loops on structurally invalid orders
            min_config = self.LIGHTER_MINIMUMS.get(symbol, self.LIGHTER_MINIMUMS['DEFAULT'])

            # Check USD minimum
            if size < min_config['usd']:
                self.logger.warning(
                    f"⚠️ SKIPPING {action} {symbol}: Position ${size:.2f} below minimum ${min_config['usd']:.2f}",
                    component="executor"
                )
                return {
                    "success": False,
                    "error": f"Position ${size:.2f} below minimum ${min_config['usd']:.2f} for {symbol}",
                    "error_type": "minimum_size_violation",
                    "symbol": symbol,
                    "action": action,
                    "current_price": current_price,
                    "retryable": False  # NOT retryable - structural constraint violation
                }

            # Check base units minimum
            if amount < min_config['base_units']:
                self.logger.warning(
                    f"⚠️ SKIPPING {action} {symbol}: Amount {amount:.6f} below minimum {min_config['base_units']:.6f} base units",
                    component="executor"
                )
                return {
                    "success": False,
                    "error": f"Amount {amount:.6f} below minimum {min_config['base_units']:.6f} base units for {symbol}",
                    "error_type": "minimum_size_violation",
                    "symbol": symbol,
                    "action": action,
                    "current_price": current_price,
                    "retryable": False  # NOT retryable - structural constraint violation
                }
        
        if dry_run:
            self.logger.info(f"[DRY-RUN] Would open {action} {symbol} position: ${size:.2f} ({amount:.6f} {symbol})")
            return {
                "success": True,
                "action": action,
                "symbol": symbol,
                "size": size,
                "entry_price": current_price,
                "dry_run": True
            }
        
        # Place order
        # Both adapters now expect: symbol, side ("buy"/"sell"), amount (USD for Lighter, base units for Pacifica)
        side = "buy" if action == "BUY" else "sell"
        # Pacifica: amount is already in base units (calculated above)
        # Lighter: adapter will convert USD to base units internally
        if adapter_name == "pacifica":
            result = await self.adapter.place_order(symbol, side, amount, reduce_only=False)
        else:
            # Lighter adapter expects USD amount, converts internally
            result = await self.adapter.place_order(symbol, side, size, reduce_only=False)
        
        # Log execution result - but IMPORTANT: Lighter returns success when order is SUBMITTED, not FILLED
        # We need to verify the order actually filled by checking positions
        if result.get('success') or result.get('status_code') == 200:
            tx_hash = result.get('tx_hash') or result.get('order_id')
            self.logger.info(f"📤 SUBMITTED: {action} {symbol} | tx_hash={tx_hash} | Verifying if actually filled...", component="executor")
            
            # Verify order actually filled by checking positions after a delay
            # Lighter orders can take a few seconds to process and appear in positions
            await asyncio.sleep(3.0)  # Wait 3 seconds for order to process (increased from 2)
            verified_fill = await self._verify_order_fill(symbol, action, size)
            
            if verified_fill:
                self.logger.info(f"✅ ACTUALLY FILLED: {action} {symbol} | tx_hash={tx_hash}", component="executor")
                return {
                    "success": True,
                    "action": action,
                    "symbol": symbol,
                    "size": size,
                    "entry_price": current_price,
                    "tx_hash": tx_hash,
                    "fill_verified": True
                }
            else:
                # Order was submitted but not filled (likely canceled by exchange)
                self.logger.warning(
                    f"⚠️ SUBMITTED BUT NOT FILLED: {action} {symbol} | tx_hash={tx_hash} | Order canceled by exchange (check slippage/limits)",
                    component="executor"
                )
                return {
                    "success": False,
                    "error": "Order submitted but not filled - likely canceled by exchange",
                    "error_type": "not_filled",
                    "symbol": symbol,
                    "action": action,
                    "current_price": current_price,
                    "tx_hash": tx_hash,
                    "retryable": True  # Can retry with updated price
                }
        else:
            # Extract full error message including slippage details
            error_msg = result.get('error') or result.get('text') or 'Unknown error'
            error_type = result.get('error_type', 'unknown')
            error_details = result.get('error_details', {})
            
            # Log with full context for LLM retry decisions
            self.logger.error(
                f"❌ Execution failed for {action} {symbol} | error={error_msg} | type={error_type} | details={error_details}",
                component="executor"
            )
            
            # Check for "invalid margin mode" - some tokens may not be tradeable
            if 'invalid margin mode' in error_msg.lower() or '21613' in str(error_details):
                self.logger.warning(
                    f"⚠️ Token {symbol} may not support margin trading (invalid margin mode). This token cannot be traded.",
                    component="executor"
                )
                error_type = "margin_mode_error"
            
            # Return detailed error info so LLM can make smart retry decisions
            return {
                "success": False,
                "error": error_msg,
                "error_type": error_type,  # 'slippage', 'unknown', 'margin_mode_error', etc.
                "error_details": error_details,  # Full error details for LLM analysis
                "symbol": symbol,
                "action": action,
                "current_price": current_price,  # So LLM can recalculate with updated price
                "retryable": error_type == 'slippage' or error_type == 'not_filled'  # Slippage and not_filled errors are retryable, but NOT margin_mode_error
            }
    
    async def _close_position(self, symbol: str, dry_run: bool) -> Dict:
        """Close existing position"""
        positions = await self.adapter.get_positions()
        position = next((p for p in positions if p.get('symbol') == symbol), None)

        if not position:
            return {"success": False, "error": f"No position found for {symbol}"}

        size = position.get('size', 0)
        entry_price = position.get('entry_price', 0)
        side = position.get('side', 'LONG')
        current_price = position.get('current_price', entry_price)  # Use price from position (already updated)

        if size == 0:
            return {"success": False, "error": f"Position size is zero for {symbol}"}

        # ✅ PRE-SUBMISSION VALIDATION FOR LIGHTER DEX
        # Check if position value meets minimum close requirements
        adapter_name = self.adapter.get_name()
        if adapter_name == "lighter":
            # Calculate position value in USD
            size_usd = position.get('size_usd', size * current_price)
            position_value = abs(size_usd)

            # Check if position meets minimum close size ($10)
            if position_value < 10.0:
                self.logger.warning(
                    f"⚠️ SKIPPING CLOSE {symbol}: Position ${position_value:.2f} below $10 minimum - cannot close on Lighter DEX",
                    component="executor"
                )
                return {
                    "success": False,
                    "error": f"Position ${position_value:.2f} below $10 minimum - cannot close on Lighter DEX",
                    "error_type": "uncloseable_position",
                    "symbol": symbol,
                    "action": "CLOSE",
                    "position_value": position_value,
                    "retryable": False  # NOT retryable - position is structurally too small
                }
        
        # Calculate P&L
        if side == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
            pnl = (current_price - entry_price) * size
        else:
            pnl_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
            pnl = (entry_price - current_price) * size
        
        if dry_run:
            self.logger.info(f"[DRY-RUN] Would close {symbol} {side} position: P&L ${pnl:.2f} ({pnl_pct*100:.2f}%)")
            return {
                "success": True,
                "action": "CLOSE",
                "symbol": symbol,
                "exit_price": current_price,
                "pnl": pnl,
                "dry_run": True
            }
        
        # Place opposite order to close
        # Convert side: LONG needs SELL, SHORT needs BUY
        opposite_action = "sell" if side == "LONG" else "buy"
        # For closing, use the actual position size
        # Both adapters handle size differently:
        # - Pacifica: size is in base units (as returned from positions)
        # - Lighter: adapter expects USD amount, converts to base units
        adapter_name = self.adapter.get_name()
        if adapter_name == "pacifica":
            # Pacifica: size is already in base units
            result = await self.adapter.place_order(symbol, opposite_action, size, reduce_only=True)
        else:
            # Lighter: adapter expects USD amount
            # Use size_usd if available, otherwise calculate
            size_usd = position.get('size_usd', size * current_price)
            result = await self.adapter.place_order(symbol, opposite_action, size_usd, reduce_only=True)
        
        # IMPORTANT: Lighter returns success when order is SUBMITTED, not FILLED
        # We need to verify the order actually filled by checking positions
        if result.get('success') or result.get('status_code') == 200:
            tx_hash = result.get('tx_hash') or result.get('order_id')
            self.logger.info(f"⚠️ CLOSE order SUBMITTED for {symbol} | tx_hash={tx_hash} | Verifying fill...", component="executor")
            
            # Verify order actually filled by checking positions after a delay
            # Lighter orders can take a few seconds to process and appear/disappear in positions
            await asyncio.sleep(3.0)  # Wait 3 seconds for order to process (increased from 2)
            verified_close = await self._verify_order_fill(symbol, "CLOSE", size)
            
            if verified_close:
                self.logger.info(f"✅ CLOSE CONFIRMED FILLED for {symbol} | tx_hash={tx_hash} | P&L: ${pnl:.2f} ({pnl_pct*100:.2f}%)", component="executor")
                return {
                    "success": True,
                    "action": "CLOSE",
                    "symbol": symbol,
                    "exit_price": current_price,
                    "pnl": pnl,
                    "tx_hash": tx_hash,
                    "fill_verified": True
                }
            else:
                # Order was submitted but not filled (likely canceled by exchange)
                self.logger.warning(
                    f"❌ CLOSE order SUBMITTED but NOT FILLED for {symbol} | tx_hash={tx_hash} | "
                    f"Position still exists - order likely canceled by exchange. Check order history.",
                    component="executor"
                )
                return {
                    "success": False,
                    "error": "CLOSE order submitted but not filled - position still exists",
                    "error_type": "not_filled",
                    "symbol": symbol,
                    "action": "CLOSE",
                    "current_price": current_price,
                    "tx_hash": tx_hash,
                    "retryable": True  # Can retry
                }
        else:
            error_msg = result.get('error') or result.get('text') or 'Unknown error'
            error_type = result.get('error_type', 'unknown')
            error_details = result.get('error_details', {})
            
            # Check for "invalid margin mode" - some tokens may not be tradeable
            if 'invalid margin mode' in error_msg.lower() or '21613' in str(error_details):
                self.logger.warning(
                    f"⚠️ Token {symbol} may not support margin trading (invalid margin mode). Skipping this token.",
                    component="executor"
                )
                error_type = "margin_mode_error"
            
            return {
                "success": False,
                "error": error_msg,
                "error_type": error_type,
                "error_details": error_details,
                "symbol": symbol,
                "action": "CLOSE",
                "retryable": error_type != "margin_mode_error"  # Don't retry margin mode errors
            }
    
    async def _verify_order_fill(self, symbol: str, action: str, expected_size: float) -> bool:
        """Verify that an order actually filled by checking positions after submission"""
        try:
            # Get current positions AFTER order submission
            positions = await self.adapter.get_positions()
            
            # Find position for this symbol
            position = next((p for p in positions if p.get('symbol') == symbol), None)
            
            if action in ['BUY', 'SELL']:
                # Opening a new position (or increasing existing)
                # For BUY: expect LONG position
                # For SELL: expect SHORT position
                if not position:
                    # No position found - order didn't fill
                    self.logger.debug(f"❌ Fill not verified: {symbol} - no position found after {action}", component="executor")
                    return False
                
                # Check position side matches action
                position_side = position.get('side', '').upper()
                is_long = position.get('is_long', True)
                
                if action == 'BUY' and not is_long:
                    self.logger.debug(f"❌ Fill not verified: {symbol} - BUY order but position is SHORT", component="executor")
                    return False
                if action == 'SELL' and is_long:
                    self.logger.debug(f"❌ Fill not verified: {symbol} - SELL order but position is LONG", component="executor")
                    return False
                
                # Position exists and side matches - order likely filled
                # We can't perfectly verify size without knowing prior size, but existence is good enough
                position_size = abs(position.get('size', 0))
                if position_size > 0:
                    self.logger.debug(f"✅ Fill verified: {symbol} {position_side} position exists with size {position_size:.6f}", component="executor")
                    return True
                else:
                    self.logger.debug(f"❌ Fill not verified: {symbol} position exists but size is 0", component="executor")
                    return False
                    
            else:
                # CLOSE action - verify position is gone or significantly reduced
                if not position:
                    # Position closed - order filled
                    self.logger.debug(f"✅ Fill verified: {symbol} position closed successfully (no position found)", component="executor")
                    return True
                else:
                    # Position still exists - check if it was significantly reduced
                    # For CLOSE, we expect the position to be gone or very small
                    position_size = abs(position.get('size', 0))
                    original_size = expected_size  # This is the size we tried to close
                    
                    # If position is gone or reduced by at least 90%, consider it closed
                    if position_size < 0.0001:
                        self.logger.debug(f"✅ Fill verified: {symbol} position reduced to near-zero ({position_size:.8f})", component="executor")
                        return True
                    elif original_size > 0 and position_size < (original_size * 0.1):
                        # Position reduced by at least 90%
                        self.logger.debug(f"✅ Fill verified: {symbol} position reduced from {original_size:.6f} to {position_size:.6f} (90%+ reduction)", component="executor")
                        return True
                    else:
                        self.logger.debug(f"❌ Fill not verified: {symbol} position still exists with size {position_size:.6f} (tried to close {original_size:.6f})", component="executor")
                        return False
                
        except Exception as e:
            self.logger.warning(f"Error verifying order fill for {symbol}: {e}", component="executor")
            # On error, assume not filled to be safe
            return False

