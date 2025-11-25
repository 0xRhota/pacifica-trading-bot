"""
Get REAL trade history from Lighter exchange API
This bypasses the tracker JSON and gets ground truth from exchange
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import lighter
from datetime import datetime, timedelta

load_dotenv()

async def get_fills_from_exchange():
    """
    Fetch actual fills/trades from Lighter exchange
    """
    # Initialize API client - use same config as bot
    url = "https://mainnet.zklighter.elliot.ai"
    account_index = 126039  # From config.py line 95

    config = lighter.Configuration(host=url)
    api_client = lighter.ApiClient(configuration=config)

    try:
        # Try different API endpoints to find trade history
        print("🔍 Searching for trade history in Lighter API...")

        # Option 1: Try fills endpoint
        try:
            fills_api = lighter.FillsApi(api_client)
            fills = await fills_api.fills(account_index=account_index, limit=100)

            if fills and hasattr(fills, 'fills'):
                print(f"\n✅ Found {len(fills.fills)} fills!\n")

                trades = []
                for fill in fills.fills:
                    trade = {
                        'timestamp': fill.timestamp if hasattr(fill, 'timestamp') else 'N/A',
                        'market_id': fill.market_id if hasattr(fill, 'market_id') else 'N/A',
                        'side': 'BUY' if not fill.is_ask else 'SELL',
                        'size': float(fill.size) if hasattr(fill, 'size') else 0,
                        'price': float(fill.price) if hasattr(fill, 'price') else 0,
                        'value': float(fill.size * fill.price) if hasattr(fill, 'size') and hasattr(fill, 'price') else 0,
                        'pnl': float(fill.realized_pnl) if hasattr(fill, 'realized_pnl') else None,
                    }
                    trades.append(trade)

                    # Print summary
                    dt = datetime.fromtimestamp(trade['timestamp']/1000) if trade['timestamp'] != 'N/A' else 'N/A'
                    print(f"{dt} | Market {trade['market_id']} | {trade['side']} | Size: {trade['size']:.4f} | Price: ${trade['price']:.4f} | Value: ${trade['value']:.2f}")
                    if trade['pnl'] is not None:
                        print(f"  └─ P&L: ${trade['pnl']:.2f}")

                # Calculate stats
                total_pnl = sum(t['pnl'] for t in trades if t['pnl'] is not None)
                wins = sum(1 for t in trades if t['pnl'] is not None and t['pnl'] > 0)
                losses = sum(1 for t in trades if t['pnl'] is not None and t['pnl'] < 0)

                print(f"\n{'='*80}")
                print(f"📊 EXCHANGE DATA SUMMARY")
                print(f"{'='*80}")
                print(f"Total Trades: {len(trades)}")
                print(f"Wins: {wins} | Losses: {losses}")
                print(f"Win Rate: {wins/(wins+losses)*100:.1f}%" if (wins+losses) > 0 else "Win Rate: N/A")
                print(f"Total P&L: ${total_pnl:.2f}")
                print(f"{'='*80}\n")

                return trades

        except AttributeError as e:
            print(f"⚠️ FillsApi not available: {e}")
        except Exception as e:
            print(f"⚠️ Error fetching fills: {e}")
            import traceback
            traceback.print_exc()

        # Option 2: Try trades endpoint (looks most promising!)
        try:
            order_api = lighter.OrderApi(api_client)

            print("\n🔍 Trying 'trades' endpoint for account...")
            trades_resp = await order_api.trades(
                account_id=str(account_index),
                limit=100
            )

            if trades_resp:
                print(f"\n✅ Found trades response!")
                print(f"Type: {type(trades_resp)}")
                print(f"Data: {trades_resp}")

                # Try to parse trades
                if hasattr(trades_resp, 'trades'):
                    print(f"\n✅ Found {len(trades_resp.trades)} trades!")
                    for trade in trades_resp.trades[:10]:  # First 10
                        print(f"Trade: {trade}")

        except TypeError as e:
            print(f"⚠️ trades() parameter error: {e}")
            print("Trying without account_id...")
            try:
                trades_resp = await order_api.trades(limit=100)
                print(f"Response: {trades_resp}")
            except Exception as e2:
                print(f"Error: {e2}")
        except Exception as e:
            print(f"⚠️ Error fetching trades: {e}")
            import traceback
            traceback.print_exc()

        # Option 3: Try export endpoint (CSV export!)
        try:
            print("\n🔍 Trying 'export' endpoint...")
            export_resp = await order_api.export(
                account_id=str(account_index)
            )

            if export_resp:
                print(f"\n✅ Export response!")
                print(f"Type: {type(export_resp)}")
                print(f"Data: {export_resp[:500] if isinstance(export_resp, str) else export_resp}")

        except Exception as e:
            print(f"⚠️ Error with export: {e}")

        # Option 4: Try account_inactive_orders (filled orders)
        try:
            print("\n🔍 Trying 'account_inactive_orders'...")
            inactive = await order_api.account_inactive_orders(
                account_id=str(account_index),
                limit=100
            )

            if inactive:
                print(f"\n✅ Inactive orders response!")
                print(f"Type: {type(inactive)}")
                if hasattr(inactive, 'orders'):
                    print(f"Found {len(inactive.orders)} inactive orders")
                    for order in inactive.orders[:5]:  # First 5
                        print(f"Order: {order}")

        except Exception as e:
            print(f"⚠️ Error with inactive orders: {e}")

        # Option 3: Try account API with more details
        try:
            account_api = lighter.AccountApi(api_client)
            account = await account_api.account(by="index", value=str(account_index))

            if account and hasattr(account, 'accounts') and account.accounts:
                acc = account.accounts[0]

                print(f"\n📊 ACCOUNT DATA:")
                print(f"  Balance: ${float(acc.balance):.2f}")
                print(f"  Available: ${float(acc.available_balance):.2f}")
                print(f"  Realized P&L: ${float(acc.realized_pnl):.2f}")

                # Check for transaction history
                if hasattr(acc, 'transactions'):
                    print(f"  Transactions: {len(acc.transactions)}")

        except Exception as e:
            print(f"⚠️ Error fetching account: {e}")

        print(f"\n⚠️ Could not find fill/trade history endpoint in Lighter API")
        print(f"Available alternatives:")
        print(f"1. Export CSV from Lighter web interface")
        print(f"2. Use WebSocket to track live fills")
        print(f"3. Query account.realized_pnl for total P&L only")

        return None

    finally:
        await api_client.close()


if __name__ == "__main__":
    asyncio.run(get_fills_from_exchange())
