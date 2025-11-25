"""
Test Hibachi order execution with a small market order

Usage:
    python3 scripts/test_hibachi_order.py          # Dry run (preview only)
    python3 scripts/test_hibachi_order.py --confirm # Execute order
"""
import asyncio
import os
import sys
import argparse
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dexes.hibachi import HibachiSDK

load_dotenv()

async def test_order(execute: bool = False):
    """Test placing a small market order on Hibachi"""

    api_key = os.getenv("HIBACHI_PUBLIC_KEY")
    api_secret = os.getenv("HIBACHI_PRIVATE_KEY")
    account_id = os.getenv("HIBACHI_ACCOUNT_ID")

    if not all([api_key, api_secret, account_id]):
        print("❌ Missing credentials in .env")
        return

    sdk = HibachiSDK(api_key, api_secret, account_id)

    print("=" * 60)
    print("🧪 HIBACHI ORDER EXECUTION TEST")
    print("=" * 60)

    # Step 1: Get current balance
    print("\n1️⃣ Checking balance...")
    balance = await sdk.get_balance()
    if balance is None:
        print("❌ Failed to get balance")
        return
    print(f"✅ Balance: ${balance:.2f} USDT")

    # Step 2: Get SOL price
    print("\n2️⃣ Getting SOL price...")
    sol_price = await sdk.get_price("SOL/USDT-P")
    if sol_price is None:
        print("❌ Failed to get SOL price")
        return
    print(f"✅ SOL Price: ${sol_price:.2f}")

    # Step 3: Calculate small position size
    # Use $2 worth of SOL (very small test)
    position_value_usd = 2.0
    sol_amount = position_value_usd / sol_price

    # Get market info for min order size
    markets = await sdk.get_markets()
    sol_market = next((m for m in markets if m['symbol'] == 'SOL/USDT-P'), None)

    if not sol_market:
        print("❌ SOL/USDT-P market not found")
        return

    min_order_size = float(sol_market['minOrderSize'])
    step_size = float(sol_market['stepSize'])

    print(f"\n3️⃣ Calculating position size...")
    print(f"   Target: ${position_value_usd} USD")
    print(f"   SOL Amount: {sol_amount:.8f} SOL")
    print(f"   Min Order Size: {min_order_size:.8f} SOL")
    print(f"   Step Size: {step_size:.8f} SOL")

    # Round to step size
    sol_amount = max(sol_amount, min_order_size)
    sol_amount = round(sol_amount / step_size) * step_size

    print(f"   Rounded Amount: {sol_amount:.8f} SOL")
    print(f"   Estimated Cost: ${sol_amount * sol_price:.2f} USDT")

    # Step 4: Check margin requirement
    initial_margin_rate = float(sol_market['initialMarginRate'])
    required_margin = sol_amount * sol_price * initial_margin_rate

    print(f"\n4️⃣ Checking margin...")
    print(f"   Initial Margin Rate: {initial_margin_rate * 100:.2f}%")
    print(f"   Required Margin: ${required_margin:.2f}")

    if required_margin > balance:
        print(f"❌ Insufficient balance (need ${required_margin:.2f}, have ${balance:.2f})")
        return

    print(f"✅ Sufficient margin available")

    # Step 5: Order preview
    print(f"\n5️⃣ Order Preview:")
    print(f"   Symbol: SOL/USDT-P")
    print(f"   Side: LONG (BUY)")
    print(f"   Amount: {sol_amount:.8f} SOL")
    print(f"   Estimated Value: ${sol_amount * sol_price:.2f} USDT")
    print(f"   Required Margin: ${required_margin:.2f} USDT")
    print(f"   Fee (0.045% taker): ${sol_amount * sol_price * 0.00045:.4f} USDT")

    if not execute:
        print("\n⚠️  DRY RUN MODE - No order will be placed")
        print("💡 Use --confirm flag to execute the order")
        print("\n" + "=" * 60)
        print("✅ DRY RUN COMPLETE")
        print("=" * 60)
        return

    print("\n⚠️  EXECUTING REAL ORDER...")

    # Step 6: Place order
    print("\n6️⃣ Placing market order...")
    order_response = await sdk.create_market_order(
        symbol="SOL/USDT-P",
        is_buy=True,
        amount=sol_amount
    )

    if order_response is None:
        print("❌ Order failed")
        return

    print(f"✅ Order placed!")
    print(f"   Response: {order_response}")

    # Step 7: Wait a bit for order to execute
    print("\n7️⃣ Waiting for order execution...")
    await asyncio.sleep(2)

    # Step 8: Check position
    print("\n8️⃣ Checking position...")
    positions = await sdk.get_positions()

    if positions:
        print(f"✅ Position opened:")
        for pos in positions:
            print(f"   {pos}")
    else:
        print("⚠️  No positions found (order may still be pending)")

    # Step 9: Check orders
    print("\n9️⃣ Checking order status...")
    orders = await sdk.get_orders(symbol="SOL/USDT-P")

    if orders:
        print(f"📋 Orders:")
        for order in orders:
            print(f"   {order}")
    else:
        print("✅ No pending orders (order filled)")

    # Step 10: Final balance check
    print("\n🔟 Final balance check...")
    final_balance = await sdk.get_balance()
    if final_balance is not None:
        balance_change = final_balance - balance
        print(f"✅ Final Balance: ${final_balance:.2f} USDT")
        print(f"   Change: ${balance_change:.2f} USDT")

    print("\n" + "=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Hibachi order execution")
    parser.add_argument("--confirm", action="store_true", help="Execute the order (default: dry run)")
    args = parser.parse_args()

    asyncio.run(test_order(execute=args.confirm))
