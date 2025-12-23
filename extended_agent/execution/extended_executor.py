"""
Extended Trade Executor
Executes LLM trading decisions using Extended SDK (Starknet)

Uses official x10-python-trading-starknet SDK for order placement
REQUIRES Python 3.10+ - run with python3.11

NOTE: Extended uses Starknet for settlement, requiring Stark signatures for orders.
API key alone is not sufficient - need Stark private/public keys from API management page.
"""

import logging
import sys
import os
import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from trade_tracker import TradeTracker

logger = logging.getLogger(__name__)


class ExtendedTradeExecutor:
    """
    Execute LLM trading decisions for Extended DEX (Starknet)

    Args:
        trading_client: Extended PerpetualTradingClient instance
        trade_tracker: TradeTracker instance for logging
        dry_run: If True, don't actually place orders (default: False)
        default_position_size: Default position size in USD
        max_positions: Max open positions (default: 10)
    """

    def __init__(
        self,
        trading_client,  # PerpetualTradingClient instance
        trade_tracker: TradeTracker,
        dry_run: bool = False,
        default_position_size: float = 50.0,  # $50 per trade
        max_positions: int = 10,
        max_position_age_minutes: int = 240  # 4 hours
    ):
        self.client = trading_client
        self.tracker = trade_tracker
        self.dry_run = dry_run
        self.default_position_size = default_position_size
        self.max_positions = max_positions
        self.max_position_age_minutes = max_position_age_minutes

        mode = "DRY-RUN" if dry_run else "LIVE"
        logger.info(f"✅ ExtendedTradeExecutor initialized ({mode} mode, ${default_position_size}/trade)")

    async def _fetch_account_balance(self) -> Optional[float]:
        """Fetch account balance from Extended API"""
        try:
            balance = await self.client.account.get_balance()
            if balance and balance.data:
                return float(balance.data.equity)
            return None
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return None

    async def _fetch_open_positions(self) -> List[Dict]:
        """Fetch current open positions from Extended API"""
        try:
            positions = await self.client.account.get_positions()
            if positions and positions.data:
                return [
                    {
                        'id': p.id,
                        'symbol': p.market,
                        'side': str(p.side).upper(),
                        'size': float(p.size),
                        'value': float(p.value),
                        'entry_price': float(p.open_price),
                        'mark_price': float(p.mark_price),
                        'unrealized_pnl': float(p.unrealised_pnl),
                        'leverage': float(p.leverage),
                    }
                    for p in positions.data
                ]
            return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def _get_market_price(self, symbol: str) -> Optional[float]:
        """Get current mark price for a symbol"""
        try:
            # Use markets_info to get current price (keyword arg required)
            stats = await self.client.markets_info.get_market_statistics(market_name=symbol)
            if stats and stats.data:
                return float(stats.data.last_price)
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    async def check_stale_positions(self) -> List[str]:
        """
        Check for stale positions and close them

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
                size = position.get('size', 0)

                if size == 0:
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
                            logger.info(f"🕐 Position {symbol} aged out ({age_minutes:.0f} min)")
                            result = await self._close_position(symbol, f"Aged {age_minutes:.0f} min")
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

        # Convert symbol format if needed (e.g., "ETH/USDT-P" -> "ETH-USD")
        symbol = self._convert_symbol(symbol)

        logger.info(f"🎯 Executing decision: {action} {symbol} - {reasoning}")

        # Fetch current positions
        positions = await self._fetch_open_positions()
        open_position_count = len([p for p in positions if p.get('size', 0) > 0])

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

    def _convert_symbol(self, symbol: str) -> str:
        """Convert internal symbol format to Extended format"""
        # Handle formats like "ETH/USDT-P" -> "ETH-USD"
        if "/" in symbol:
            base = symbol.split("/")[0]
            return f"{base}-USD"
        # Already in Extended format
        if "-USD" in symbol:
            return symbol
        # Just base asset
        return f"{symbol}-USD"

    async def _open_position(self, action: str, symbol: str, reason: str, decision: Dict = None) -> Dict:
        """
        Open a new position

        Args:
            action: "LONG" or "SHORT"
            symbol: Trading symbol (Extended format, e.g., "BTC-USD")
            reason: Reasoning for the trade
            decision: Full decision dict

        Returns:
            Dict with execution result
        """
        try:
            # Get current price
            price = await self._get_market_price(symbol)
            if not price:
                logger.error(f"❌ Cannot get price for {symbol}")
                return {
                    'success': False,
                    'action': action,
                    'symbol': symbol,
                    'error': 'Cannot get price'
                }

            # Position sizing with leverage
            confidence = decision.get('confidence', 0.5) if decision else 0.5
            account_balance = await self._fetch_account_balance()

            # Leverage scaling based on confidence
            BASE_LEVERAGE = 3.0
            MAX_LEVERAGE = 5.0

            if account_balance and account_balance > 1.0:
                # 2025-12-08: Increased sizing 3x to test if whale edge can overcome fees
                # Previous: base_pct=0.40, max=$500 → ~$120 positions
                # New: base_pct=0.80, max=$1000 → ~$350 positions
                if confidence < 0.5:
                    leverage = BASE_LEVERAGE
                elif confidence < 0.7:
                    leverage = BASE_LEVERAGE + 0.5
                elif confidence < 0.85:
                    leverage = BASE_LEVERAGE + 1.0
                else:
                    leverage = MAX_LEVERAGE

                base_pct = 0.80  # Increased from 0.40 (2x)
                position_size_usd = account_balance * base_pct * leverage
                position_size_usd = max(100.0, min(position_size_usd, 1000.0))  # Min $100, max $1000

                logger.info(
                    f"🚀 Leveraged sizing: ${account_balance:.2f} balance × {leverage:.1f}x | "
                    f"conf={confidence:.2f} → ${position_size_usd:.2f} notional"
                )
            else:
                position_size_usd = 50.0
                leverage = BASE_LEVERAGE
                logger.warning(f"Using minimum size ($50) - balance: {account_balance}")

            # Calculate amount with proper precision per market
            # Extended asset_precision: BTC=5, ETH=3, SOL=2
            raw_amount = position_size_usd / price

            # Round to market-specific precision (from Extended API)
            if "BTC" in symbol:
                precision = 5  # min_order_size_change=0.00001 BTC
            elif "ETH" in symbol:
                precision = 3  # min_order_size_change=0.001 ETH
            else:  # SOL and others
                precision = 2  # min_order_size_change=0.01 SOL

            amount = Decimal(str(round(raw_amount, precision)))

            # Import order side from SDK
            from x10.perpetual.orders import OrderSide
            side = OrderSide.BUY if action == "LONG" else OrderSide.SELL

            logger.info(f"{'📈' if action == 'LONG' else '📉'} {action} {symbol}: {amount:.6f} @ ${price:.2f}")
            logger.info(f"   Reason: {reason}")

            if self.dry_run:
                logger.info(f"🏃 DRY-RUN: Would place {action} order for {amount:.6f} {symbol}")

                self.tracker.log_entry(
                    order_id=None,
                    symbol=symbol,
                    side=action.lower(),
                    entry_price=price,
                    size=float(amount),
                    notes=reason
                )

                return {
                    'success': True,
                    'action': action,
                    'symbol': symbol,
                    'price': price,
                    'amount': float(amount),
                    'dry_run': True
                }

            # Execute real order using Extended SDK
            # Price needs some slippage buffer for market-like execution
            from x10.perpetual.orders import TimeInForce

            order_price = price * 1.005 if action == "LONG" else price * 0.995  # 0.5% slippage

            order = await self.client.place_order(
                market_name=symbol,
                amount_of_synthetic=amount,
                price=Decimal(str(int(order_price))),  # Price as integer
                side=side,
                time_in_force=TimeInForce.GTT,
                expire_time=datetime.now(timezone.utc) + timedelta(hours=1),  # 1 hour expiry
            )

            if order and order.data:
                order_id = str(order.data.id)
                logger.info(f"✅ Order placed: {order_id}")

                self.tracker.log_entry(
                    order_id=order_id,
                    symbol=symbol,
                    side=action.lower(),
                    entry_price=price,
                    size=float(amount),
                    notes=reason
                )

                return {
                    'success': True,
                    'action': action,
                    'symbol': symbol,
                    'price': price,
                    'amount': float(amount),
                    'order_id': order_id
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

            size = position.get('size', 0)
            side = position.get('side')
            entry_price = position.get('entry_price', 0)

            if size == 0:
                logger.warning(f"⚠️  Position {symbol} has zero size")
                return {
                    'success': False,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'error': 'Zero size'
                }

            # Close position (opposite of current side)
            from x10.perpetual.orders import OrderSide
            close_side = OrderSide.SELL if side == 'LONG' else OrderSide.BUY

            price = await self._get_market_price(symbol)

            # Calculate P/L
            # LONG: profit when exit > entry
            # SHORT: profit when entry > exit
            if price and entry_price:
                if side == 'LONG':
                    pnl = (price - entry_price) * size
                else:  # SHORT
                    pnl = (entry_price - price) * size
            else:
                pnl = 0
                logger.warning(f"⚠️  Cannot calculate P/L for {symbol} - price: {price}, entry: {entry_price}")

            logger.info(f"🔴 CLOSE {symbol}: {size:.6f} (Side: {side})")
            logger.info(f"   Reason: {reason}")

            if self.dry_run:
                logger.info(f"🏃 DRY-RUN: Would close {symbol} position")

                tracker_pos = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_pos:
                    self.tracker.log_exit(
                        order_id=tracker_pos.get('order_id'),
                        exit_price=price if price else 0,
                        exit_reason=reason
                    )

                return {
                    'success': True,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'size': size,
                    'price': price if price else 0,
                    'pnl': pnl,
                    'dry_run': True
                }

            # Execute close order
            from x10.perpetual.orders import TimeInForce

            close_price = price * 0.995 if close_side == OrderSide.SELL else price * 1.005

            order = await self.client.place_order(
                market_name=symbol,
                amount_of_synthetic=Decimal(str(size)),
                price=Decimal(str(int(close_price))),
                side=close_side,
                reduce_only=True,
                time_in_force=TimeInForce.GTT,
                expire_time=datetime.now(timezone.utc) + timedelta(hours=1),
            )

            if order and order.data:
                order_id = str(order.data.id)
                logger.info(f"✅ Position closed: {order_id} | P/L: ${pnl:.2f}")

                tracker_pos = self.tracker.get_open_trade_for_symbol(symbol)
                if tracker_pos:
                    self.tracker.log_exit(
                        order_id=tracker_pos.get('order_id'),
                        exit_price=price if price else 0,
                        exit_reason=reason
                    )

                return {
                    'success': True,
                    'action': 'CLOSE',
                    'symbol': symbol,
                    'size': size,
                    'price': price if price else 0,
                    'pnl': pnl,
                    'order_id': order_id
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


def create_extended_executor_from_env(
    trade_tracker: TradeTracker,
    dry_run: bool = False,
    testnet: bool = False
) -> Optional[ExtendedTradeExecutor]:
    """
    Create Extended executor from environment variables

    Required env vars:
        EXTENDED or EXTENDED_API_KEY: API key
        EXTENDED_STARK_PRIVATE_KEY: Stark private key
        EXTENDED_STARK_PUBLIC_KEY: Stark public key
        EXTENDED_VAULT: Vault/position ID

    Get these from: https://app.extended.exchange/api-management
    """
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("EXTENDED") or os.getenv("EXTENDED_API_KEY")
    private_key = os.getenv("EXTENDED_STARK_PRIVATE_KEY")
    public_key = os.getenv("EXTENDED_STARK_PUBLIC_KEY")
    vault = os.getenv("EXTENDED_VAULT")

    if not api_key:
        logger.error("EXTENDED or EXTENDED_API_KEY not set")
        return None

    if not all([private_key, public_key, vault]):
        logger.error(
            "Missing Extended credentials. Required:\n"
            "  - EXTENDED_STARK_PRIVATE_KEY\n"
            "  - EXTENDED_STARK_PUBLIC_KEY\n"
            "  - EXTENDED_VAULT\n"
            "Get these from: https://app.extended.exchange/api-management"
        )
        return None

    try:
        from x10.perpetual.accounts import StarkPerpetualAccount
        from x10.perpetual.configuration import MAINNET_CONFIG, TESTNET_CONFIG
        from x10.perpetual.trading_client import PerpetualTradingClient

        config = TESTNET_CONFIG if testnet else MAINNET_CONFIG

        stark_account = StarkPerpetualAccount(
            vault=int(vault),
            private_key=private_key,
            public_key=public_key,
            api_key=api_key,
        )

        # Create trading client (direct instantiation, not .create())
        trading_client = PerpetualTradingClient(
            endpoint_config=config,
            stark_account=stark_account
        )

        return ExtendedTradeExecutor(
            trading_client=trading_client,
            trade_tracker=trade_tracker,
            dry_run=dry_run,
        )

    except Exception as e:
        logger.error(f"Failed to create Extended executor: {e}")
        return None


# Test the executor
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(level=logging.INFO)

    async def test():
        # Check if we have credentials
        api_key = os.getenv("EXTENDED") or os.getenv("EXTENDED_API_KEY")
        private_key = os.getenv("EXTENDED_STARK_PRIVATE_KEY")
        public_key = os.getenv("EXTENDED_STARK_PUBLIC_KEY")
        vault = os.getenv("EXTENDED_VAULT")

        print("Extended credentials check:")
        print(f"  API Key: {'✅' if api_key else '❌'}")
        print(f"  Stark Private Key: {'✅' if private_key else '❌'}")
        print(f"  Stark Public Key: {'✅' if public_key else '❌'}")
        print(f"  Vault: {'✅' if vault else '❌'}")

        if not all([api_key, private_key, public_key, vault]):
            print("\n⚠️  Missing credentials!")
            print("Get them from: https://app.extended.exchange/api-management")
            return

        # Create executor
        tracker = TradeTracker(dex="extended", log_dir="logs")
        executor = create_extended_executor_from_env(tracker, dry_run=True)

        if executor:
            print("\n✅ Executor created successfully!")

            # Test fetching positions
            positions = await executor._fetch_open_positions()
            print(f"Open positions: {len(positions)}")

            # Test fetching balance
            balance = await executor._fetch_account_balance()
            print(f"Balance: ${balance:.2f}" if balance else "Balance: N/A")

            # Test fetching price
            price = await executor._get_market_price("BTC-USD")
            print(f"BTC Price: ${price:,.2f}" if price else "BTC Price: N/A")

            # Close client
            await executor.client.close()

    asyncio.run(test())
