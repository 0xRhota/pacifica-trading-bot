"""
Lighter DEX SDK Wrapper
Working implementation using create_market_order
"""

import asyncio
import lighter
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


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
        """Get all open positions"""
        try:
            account = await self.account_api.account(
                by="index",
                value=str(self.account_index)
            )

            positions = []

            if hasattr(account, 'accounts') and account.accounts:
                acc = account.accounts[0]

                if hasattr(acc, 'positions'):
                    for pos in acc.positions:
                        if float(pos.position) != 0:
                            positions.append({
                                'market_id': pos.market_id,
                                'size': float(pos.position),
                                'entry_price': float(pos.avg_entry_price),
                                'value': float(pos.position_value),
                                'pnl': float(pos.unrealized_pnl) if hasattr(pos, 'unrealized_pnl') else 0
                            })

            return {'success': True, 'data': positions}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def create_market_order(self, symbol: str, side: str, amount: float) -> Dict:
        """
        Create market order

        Args:
            symbol: Trading symbol (SOL, BTC, etc)
            side: 'bid' for buy, 'ask' for sell
            amount: Size in base units (e.g., 0.050 for SOL)

        Returns:
            Dict with success, tx_hash, and error
        """
        # Market ID mapping (verified working)
        MARKET_IDS = {
            'BTC': 1,
            'SOL': 2,
            'ETH': 3,
            'PENGU': 4,  # User confirmed exists
            'XPL': 5,    # User confirmed exists
            'ASTER': 6,  # User confirmed exists
        }

        # Market decimals (for converting float to int)
        DECIMALS = {
            'BTC': 6,    # 0.001 = 1000
            'SOL': 3,    # 0.050 = 50
            'ETH': 4,    # 0.01 = 100
            'PENGU': 0,  # Whole numbers (price ~$0.03)
            'XPL': 2,    # 0.01 precision (price ~$0.92)
            'ASTER': 2,  # 0.01 precision (price ~$2.11)
        }

        try:
            market_id = MARKET_IDS.get(symbol)
            if not market_id:
                return {'success': False, 'error': f'Unknown symbol: {symbol}'}

            decimals = DECIMALS.get(symbol, 3)

            # Convert to integer with decimals
            base_amount = int(amount * (10 ** decimals))

            # Generate unique order ID
            import time
            client_order_index = int(time.time() * 1000) % 1000000

            # Get rough market price for avg_execution_price
            # Use a high price for buys, low for sells to ensure fill
            if side == 'bid':  # BUY
                avg_price = 1000000  # High price
                is_ask = False
            else:  # SELL
                avg_price = 1  # Low price
                is_ask = True

            print(f"📝 Lighter order: {side.upper()} {amount} {symbol}")
            print(f"   Market ID: {market_id}")
            print(f"   Base Amount: {base_amount}")

            # Use create_market_order - this method WORKS
            result = await self.signer_client.create_market_order(
                market_index=market_id,
                client_order_index=client_order_index,
                base_amount=base_amount,
                avg_execution_price=avg_price,
                is_ask=is_ask,
                reduce_only=False
            )

            if result:
                tx, tx_hash, error = result

                if error:
                    return {'success': False, 'error': error}

                return {
                    'success': True,
                    'tx_hash': tx_hash.tx_hash if hasattr(tx_hash, 'tx_hash') else str(tx_hash),
                    'message': 'Order submitted'
                }

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
