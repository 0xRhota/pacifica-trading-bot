"""
Lighter DEX SDK Wrapper
Working implementation using create_market_order
"""

import asyncio
import lighter
import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LighterSDK:
    """Simple wrapper for Lighter trading"""

    def __init__(self, private_key: str, account_index: int, api_key_index: int):
        self.url = "https://mainnet.zklighter.elliot.ai"
        self.private_key = private_key
        self.account_index = account_index
        self.api_key_index = api_key_index

        self.signer_client = lighter.SignerClient(
            url=self.url,
            private_key=private_key,
            account_index=account_index,
            api_key_index=api_key_index,
        )

        config = lighter.Configuration(host=self.url)
        self.api_client = lighter.ApiClient(configuration=config)
        self.account_api = lighter.AccountApi(self.api_client)
        self.order_api = lighter.OrderApi(self.api_client)  # Initialize for trade history
        self.transaction_api = lighter.TransactionApi(self.api_client)  # For transaction history
        self._market_id_to_symbol = None  # Cached mapping, fetched dynamically
        self._market_metadata = None  # Cached market metadata (decimals, etc)

    async def _fetch_market_metadata(self) -> Dict[int, Dict]:
        """
        Fetch market metadata from orderBooks API
        Returns dict mapping market_id -> {price_decimals, size_decimals, symbol, ...}
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/api/v1/orderBooks") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        metadata = {}
                        for market in data.get('order_books', []):
                            market_id = market.get('market_id')
                            if market_id:
                                metadata[market_id] = {
                                    'symbol': market.get('symbol'),
                                    'price_decimals': market.get('supported_price_decimals', 3),
                                    'size_decimals': market.get('supported_size_decimals', 3),
                                    'status': market.get('status', 'unknown')
                                }
                        logger.info(f"✅ Fetched metadata for {len(metadata)} markets")
                        return metadata
                    else:
                        logger.error(f"Failed to fetch market metadata: HTTP {resp.status}")
                        return {}
        except Exception as e:
            logger.error(f"Error fetching market metadata: {e}")
            return {}

    async def get_balance(self) -> Optional[float]:
        """Get account balance"""
        try:
            account = await self.account_api.account(
                by="index",
                value=str(self.account_index)
            )

            if hasattr(account, 'accounts') and account.accounts:
                acc = account.accounts[0]
                return float(acc.available_balance)

            return None

        except Exception as e:
            print(f"Error getting balance: {e}")
            return None

    async def get_positions(self) -> Dict:
        """Get all open positions with symbol names from API metadata"""
        try:
            # Fetch market metadata if not cached (gets symbol names from API)
            if self._market_metadata is None:
                self._market_metadata = await self._fetch_market_metadata()

            account = await self.account_api.account(
                by="index",
                value=str(self.account_index)
            )

            positions = []

            if hasattr(account, 'accounts') and account.accounts:
                acc = account.accounts[0]

                if hasattr(acc, 'positions'):
                    for pos in acc.positions:
                        position_size = float(pos.position)
                        if position_size != 0:
                            # CRITICAL FIX: Use 'sign' field to determine direction
                            # sign=1 means LONG, sign=-1 means SHORT
                            # The 'position' field is always positive (absolute value)
                            sign_value = getattr(pos, 'sign', 1)  # Default to LONG if missing
                            is_long = (sign_value == 1)

                            # Get symbol from API metadata (single source of truth)
                            symbol = 'UNKNOWN'
                            if pos.market_id in self._market_metadata:
                                symbol = self._market_metadata[pos.market_id].get('symbol', f'UNKNOWN(market_id={pos.market_id})')

                            logger.debug(f"📍 Position: market_id={pos.market_id}, symbol={symbol}, size={position_size}, sign={sign_value}, is_long={is_long}")

                            positions.append({
                                'market_id': pos.market_id,
                                'symbol': symbol,  # Now includes correct symbol from API
                                'size': abs(position_size),  # Store absolute value
                                'size_raw': position_size * sign_value,  # Apply sign for legacy compatibility
                                'is_long': is_long,
                                'side': 'LONG' if is_long else 'SHORT',
                                'entry_price': float(pos.avg_entry_price),
                                'value': float(pos.position_value),
                                'pnl': float(pos.unrealized_pnl) if hasattr(pos, 'unrealized_pnl') else 0
                            })

            return {'success': True, 'data': positions}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_trade_history(self, limit: int = 100, hours: int = 24) -> Dict:
        """
        Get trade history from exchange API using account transactions

        Args:
            limit: Maximum number of transactions to fetch (1-100)
            hours: Only include trades from last N hours (default 24)

        Returns:
            Dict with:
                - trades: List of trade objects
                - total_pnl: Total P&L from account data
                - win_rate: Win percentage
                - wins: Number of winning trades
                - losses: Number of losing trades
                - symbol_stats: Per-symbol statistics
        """
        try:
            # Fetch market metadata for symbol names
            if self._market_metadata is None:
                self._market_metadata = await self._fetch_market_metadata()

            # Get account data first for realized P&L
            account = await self.account_api.account(
                by="index",
                value=str(self.account_index)
            )

            total_realized_pnl = 0
            if hasattr(account, 'accounts') and account.accounts:
                acc = account.accounts[0]
                # Get realized P&L from account
                total_realized_pnl = float(getattr(acc, 'realized_pnl', 0))

            logger.info(f"📊 Account realized P&L: ${total_realized_pnl:.2f}")

            # Use AccountApi to get account data with positions history
            # This is simpler and more reliable than transaction API
            # We can calculate stats from current positions + realized P&L

            return {
                'success': True,
                'total_pnl': total_realized_pnl,
                'note': 'Using account realized_pnl field - full trade history parsing requires WebSocket or different API approach'
            }

        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    async def get_all_market_symbols(self) -> list:
        """
        Get list of all available market symbols from API metadata

        Returns:
            List of symbol strings (e.g., ['BTC', 'SOL', 'DOGE', '1000PEPE', 'WIF', 'WLD'])
        """
        # Ensure metadata is fetched
        if self._market_metadata is None:
            self._market_metadata = await self._fetch_market_metadata()

        # Extract symbols from metadata
        symbols = []
        for market_id, metadata in self._market_metadata.items():
            symbol = metadata.get('symbol')
            if symbol:
                symbols.append(symbol)

        return sorted(symbols)  # Sort for consistent ordering

    async def get_market_id_for_symbol(self, symbol: str) -> Optional[int]:
        """
        Reverse lookup: get market_id for a given symbol

        Args:
            symbol: Trading symbol (e.g., 'SOL', 'DOGE', '1000PEPE')

        Returns:
            market_id (int) or None if not found
        """
        # Ensure metadata is fetched
        if self._market_metadata is None:
            self._market_metadata = await self._fetch_market_metadata()

        # Search for symbol in metadata
        for market_id, metadata in self._market_metadata.items():
            if metadata.get('symbol') == symbol:
                return market_id

        return None

    async def get_current_price(self, symbol: str, market_id: int = None) -> Optional[float]:
        """
        Fetch current market price from latest 1m candlestick

        Args:
            symbol: Token symbol (e.g., 'SOL')
            market_id: Optional market_id (will lookup if not provided)

        Returns:
            Current price or None if unavailable
        """
        # Fallback market IDs
        FALLBACK_MARKET_IDS = {
            'BTC': 1, 'SOL': 2, 'ETH': 3,
            'PENGU': 4, 'XPL': 5, 'ASTER': 6,
        }

        try:
            if market_id is None:
                market_id = FALLBACK_MARKET_IDS.get(symbol)
                if not market_id:
                    return None

            # Fetch latest 1m candle
            import lighter
            import time
            config = lighter.Configuration(host='https://mainnet.zklighter.elliot.ai')
            async with lighter.ApiClient(config) as api_client:
                api = lighter.CandlestickApi(api_client)
                # Get 1 candle from 1m resolution (most recent)
                end_time = int(time.time() * 1000)
                start_time = end_time - (60 * 1000)  # 1 minute ago

                result = await api.candlesticks(
                    market_id=market_id,
                    resolution="1m",  # 1m resolution
                    start_timestamp=start_time,
                    end_timestamp=end_time,
                    count_back=1
                )

                if result and hasattr(result, 'candlesticks') and result.candlesticks:
                    # Get most recent candle's close price
                    latest_candle = result.candlesticks[-1]
                    if hasattr(latest_candle, 'close'):
                        return float(latest_candle.close)

            return None

        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None

    async def create_market_order(self, symbol: str, side: str, amount: float, reduce_only: bool = False, market_id: int = None, decimals: int = None, current_price: float = None) -> Dict:
        """
        Create market order - NOW SUPPORTS DYNAMIC MARKETS

        Args:
            symbol: Trading symbol (SOL, BTC, etc)
            side: 'bid' for buy, 'ask' for sell
            amount: Size in base units (e.g., 0.050 for SOL)
            reduce_only: If True, only reduce existing position (for closing)
            market_id: Optional - if provided, use this instead of lookup
            decimals: Optional - if provided, use this instead of lookup

        Returns:
            Dict with success, tx_hash, and error
        """
        # Fallback market ID mapping (for backward compatibility)
        FALLBACK_MARKET_IDS = {
            'BTC': 1, 'SOL': 2, 'ETH': 3,
            'PENGU': 4, 'XPL': 5, 'ASTER': 6,
        }
        
        # Fallback decimals for BASE AMOUNT (for backward compatibility)
        FALLBACK_DECIMALS = {
            'BTC': 5, 'SOL': 3, 'DOGE': 0,
            '1000PEPE': 0, 'WIF': 1, 'WLD': 1,
            # ALIASES: XPL=WIF, ASTER=WLD (internal symbols)
            'XPL': 1, 'ASTER': 1,
        }

        # CRITICAL: Price decimals are DIFFERENT from base amount decimals!
        # These come from supported_price_decimals in orderBooks API
        PRICE_DECIMALS = {
            'BTC': 1, 'SOL': 3, 'DOGE': 6,
            '1000PEPE': 6, 'WIF': 5, 'WLD': 5,
            # ALIASES: XPL=WIF, ASTER=WLD (internal symbols)
            'XPL': 5, 'ASTER': 5,
        }

        try:
            # Fetch market metadata if not cached
            if self._market_metadata is None:
                self._market_metadata = await self._fetch_market_metadata()

            # Use provided market_id/decimals or fallback to hardcoded (for backward compatibility)
            if market_id is None:
                market_id = FALLBACK_MARKET_IDS.get(symbol)
                if not market_id:
                    return {'success': False, 'error': f'Unknown symbol: {symbol} (provide market_id for dynamic markets)'}

            # Try to get decimals from cached metadata first
            size_decimals = decimals
            price_decimals = None

            if market_id in self._market_metadata:
                market_info = self._market_metadata[market_id]
                if size_decimals is None:
                    size_decimals = market_info.get('size_decimals', 3)
                price_decimals = market_info.get('price_decimals', 3)
                logger.debug(f"Using metadata for market_id={market_id}: size_decimals={size_decimals}, price_decimals={price_decimals}")
            else:
                # Fall back to hardcoded values if metadata not available
                if size_decimals is None:
                    size_decimals = FALLBACK_DECIMALS.get(symbol, 3)
                price_decimals = PRICE_DECIMALS.get(symbol, 3)
                logger.warning(f"⚠️ No metadata for market_id={market_id}, using fallback: size_decimals={size_decimals}, price_decimals={price_decimals}")

            # Convert to integer with decimals
            base_amount = int(amount * (10 ** size_decimals))

            # Generate unique order ID
            import time
            client_order_index = int(time.time() * 1000) % 1000000

            # Calculate avg_execution_price based on order type
            # CRITICAL: Price uses MARKET-SPECIFIC price decimals (from supported_price_decimals)
            # NOT the same as base amount decimals!

            # Use current_price if available (for both regular and reduce-only orders)
            if current_price and current_price > 0:
                # CRITICAL FIX: Market orders need slippage tolerance to cross the spread
                # Using exact mid price causes "excessive slippage" cancellations
                # Add 2% buffer to ensure orders can execute
                if side == 'bid':  # BUY - need to lift the ask
                    execution_price = current_price * 1.02  # 2% above market
                else:  # SELL - need to hit the bid
                    execution_price = current_price * 0.98  # 2% below market

                scaled_price = int(execution_price * (10 ** price_decimals))
                if scaled_price == 0:  # Zero-price guard
                    scaled_price = 1
                avg_price = scaled_price
            else:
                # Fallback: no price available, use extreme values
                if side == 'bid':  # BUY
                    avg_price = 1000000  # Extreme high
                else:  # SELL
                    avg_price = 1  # Extreme low

            is_ask = (side == 'ask')

            print(f"📝 Lighter order: {side.upper()} {amount} {symbol}")
            print(f"   Market ID: {market_id}")
            print(f"   Base Amount: {base_amount}")
            print(f"   Avg Price: {avg_price} | Reduce Only: {reduce_only} | Current Price: {current_price}")

            # Use create_market_order - this method WORKS
            result = await self.signer_client.create_market_order(
                market_index=market_id,
                client_order_index=client_order_index,
                base_amount=base_amount,
                avg_execution_price=avg_price,
                is_ask=is_ask,
                reduce_only=reduce_only
            )

            if result:
                try:
                    # Log result for debugging
                    print(f"📥 Raw result type: {type(result)}, value: {result}")
                    
                    # Unpack result - should be (tx, tx_hash, error) or similar
                    if isinstance(result, tuple):
                        if len(result) == 3:
                            tx, tx_hash, error = result
                            print(f"   Unpacked: tx={type(tx)}, tx_hash={type(tx_hash)}, error={type(error)}")
                        elif len(result) == 2:
                            tx_hash, error = result
                            tx = None
                            print(f"   Unpacked (2-tuple): tx_hash={type(tx_hash)}, error={type(error)}")
                        else:
                            return {'success': False, 'error': f'Unexpected tuple length: {len(result)}, result: {result}'}
                    else:
                        # Result might be a single object or different format
                        print(f"   Result is not a tuple, type: {type(result)}")
                        return {'success': False, 'error': f'Unexpected result type: {type(result)}, result: {result}'}

                    # Check for error - handle None safely
                    # Extract FULL error message including slippage reasons
                    if error is not None:
                        # Handle error object safely - extract ALL available error info
                        try:
                            error_details = {}
                            error_str = None
                            
                            # Try to extract all possible error attributes
                            if isinstance(error, str):
                                error_str = error
                            elif error is None:
                                error_str = 'Unknown error (None)'
                            else:
                                # Check for common error attributes - use getattr with safe defaults
                                code = getattr(error, 'code', None)
                                if code is not None:
                                    error_details['code'] = code
                                message = getattr(error, 'message', None)
                                if message is not None:
                                    error_details['message'] = message
                                reason = getattr(error, 'reason', None)
                                if reason is not None:
                                    error_details['reason'] = reason
                                details = getattr(error, 'details', None)
                                if details is not None:
                                    error_details['details'] = details
                                slippage = getattr(error, 'slippage', None)
                                if slippage is not None:
                                    error_details['slippage'] = slippage
                                
                                # Build comprehensive error string
                                if error_details.get('message'):
                                    error_str = error_details['message']
                                    if error_details.get('reason'):
                                        error_str += f" | Reason: {error_details['reason']}"
                                    if error_details.get('code'):
                                        error_str += f" | Code: {error_details['code']}"
                                elif error_details.get('reason'):
                                    error_str = error_details['reason']
                                elif error_details.get('code'):
                                    error_str = f"Error code {error_details['code']}: {error}"
                                else:
                                    error_str = str(error)
                            
                            # Return detailed error info for LLM retry logic
                            return {
                                'success': False, 
                                'error': error_str,
                                'error_details': error_details,  # Pass full details for LLM
                                'error_type': 'slippage' if 'slippage' in error_str.lower() else 'unknown'
                            }
                        except AttributeError as attr_err:
                            error_str = str(error) if error else 'Unknown error'
                            return {
                                'success': False, 
                                'error': f'Error accessing error attributes: {attr_err}, error type: {type(error)}, raw: {error_str}',
                                'error_details': {'raw_error': str(error)},
                                'error_type': 'parse_error'
                            }

                    # Extract tx_hash safely
                    try:
                        if tx_hash:
                            if hasattr(tx_hash, 'tx_hash'):
                                tx_hash_str = tx_hash.tx_hash if tx_hash.tx_hash is not None else str(tx_hash)
                            else:
                                tx_hash_str = str(tx_hash)
                        else:
                            tx_hash_str = str(tx) if tx else "unknown"
                    except Exception as tx_err:
                        return {'success': False, 'error': f'Error extracting tx_hash: {tx_err}'}

                    return {
                        'success': True,
                        'tx_hash': tx_hash_str,
                        'message': 'Order submitted'
                    }
                except (ValueError, TypeError, AttributeError) as e:
                    # Result might not be in expected format
                    import traceback
                    tb = traceback.format_exc()
                    return {'success': False, 'error': f'Error processing result: {e}, result type: {type(result)}, result: {result}, traceback: {tb}'}

            return {'success': False, 'error': 'No result returned'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def create_stop_loss_order(self, symbol: str, position_size: float,
                                     entry_price: float, is_long: bool,
                                     stop_loss_pct: float = 0.01) -> Dict:
        """
        Create stop-loss order for position

        Args:
            symbol: Trading symbol
            position_size: Size of position to protect
            entry_price: Entry price of position
            is_long: True if protecting long, False if protecting short
            stop_loss_pct: Stop loss percentage (default 1%)

        Returns:
            Dict with success/error
        """
        MARKET_IDS = {
            'BTC': 1, 'SOL': 2, 'ETH': 3,
            'PENGU': 4, 'XPL': 5, 'ASTER': 6,
        }
        DECIMALS = {
            'BTC': 6, 'SOL': 3, 'ETH': 4,
            'PENGU': 0, 'XPL': 2, 'ASTER': 2,
        }

        try:
            market_id = MARKET_IDS.get(symbol)
            if not market_id:
                return {'success': False, 'error': f'Unknown symbol: {symbol}'}

            decimals = DECIMALS.get(symbol, 3)
            base_amount = int(position_size * (10 ** decimals))

            # Calculate stop price
            if is_long:
                # Long position: stop if price drops below entry - stop_loss_pct
                trigger_price = entry_price * (1 - stop_loss_pct)
                is_ask = True  # Sell to close long
            else:
                # Short position: stop if price rises above entry + stop_loss_pct
                trigger_price = entry_price * (1 + stop_loss_pct)
                is_ask = False  # Buy to close short

            # Convert to integer price
            price = int(trigger_price * (10 ** decimals))

            import time
            client_order_index = int(time.time() * 1000) % 1000000

            print(f"📝 Stop Loss: {symbol} @ ${trigger_price:.4f} (entry ${entry_price:.4f})")

            result = await self.signer_client.create_sl_order(
                market_index=market_id,
                client_order_index=client_order_index,
                base_amount=base_amount,
                trigger_price=price,
                price=price,
                is_ask=is_ask,
                reduce_only=True
            )

            if result:
                tx, tx_hash, error = result
                if error:
                    return {'success': False, 'error': error}
                return {
                    'success': True,
                    'tx_hash': tx_hash.tx_hash if hasattr(tx_hash, 'tx_hash') else str(tx_hash)
                }

            return {'success': False, 'error': 'No result returned'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def create_take_profit_order(self, symbol: str, position_size: float,
                                      entry_price: float, is_long: bool,
                                      take_profit_pct: float = 0.025) -> Dict:
        """
        Create take-profit order for position

        Args:
            symbol: Trading symbol
            position_size: Size of position
            entry_price: Entry price
            is_long: True if long position
            take_profit_pct: Take profit percentage (default 2.5%)

        Returns:
            Dict with success/error
        """
        MARKET_IDS = {
            'BTC': 1, 'SOL': 2, 'ETH': 3,
            'PENGU': 4, 'XPL': 5, 'ASTER': 6,
        }
        DECIMALS = {
            'BTC': 6, 'SOL': 3, 'ETH': 4,
            'PENGU': 0, 'XPL': 2, 'ASTER': 2,
        }

        try:
            market_id = MARKET_IDS.get(symbol)
            if not market_id:
                return {'success': False, 'error': f'Unknown symbol: {symbol}'}

            decimals = DECIMALS.get(symbol, 3)
            base_amount = int(position_size * (10 ** decimals))

            # Calculate TP price
            if is_long:
                # Long: TP if price rises above entry + take_profit_pct
                trigger_price = entry_price * (1 + take_profit_pct)
                is_ask = True  # Sell to close long
            else:
                # Short: TP if price drops below entry - take_profit_pct
                trigger_price = entry_price * (1 - take_profit_pct)
                is_ask = False  # Buy to close short

            price = int(trigger_price * (10 ** decimals))

            import time
            client_order_index = int(time.time() * 1000) % 1000000

            print(f"📝 Take Profit: {symbol} @ ${trigger_price:.4f} (entry ${entry_price:.4f})")

            result = await self.signer_client.create_tp_order(
                market_index=market_id,
                client_order_index=client_order_index,
                base_amount=base_amount,
                trigger_price=price,
                price=price,
                is_ask=is_ask,
                reduce_only=True
            )

            if result:
                tx, tx_hash, error = result
                if error:
                    return {'success': False, 'error': error}
                return {
                    'success': True,
                    'tx_hash': tx_hash.tx_hash if hasattr(tx_hash, 'tx_hash') else str(tx_hash)
                }

            return {'success': False, 'error': 'No result returned'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def close(self):
        """Close connections"""
        await self.api_client.close()
        await self.signer_client.close()


# Example usage
if __name__ == "__main__":
    async def test():
        sdk = LighterSDK(
            private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
            account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
            api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX"))
        )

        # Get balance
        balance = await sdk.get_balance()
        print(f"💰 Balance: ${balance:.2f}")

        # Get positions
        positions = await sdk.get_positions()
        print(f"📊 Positions: {positions}")

        await sdk.close()

    asyncio.run(test())
