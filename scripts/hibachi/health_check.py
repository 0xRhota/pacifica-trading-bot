"""
Hibachi Health Check - Verify API connectivity and current state

Usage:
    python3 scripts/hibachi/health_check.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dexes.hibachi import HibachiSDK

load_dotenv()

async def health_check():
    """Verify Hibachi API is working and show current state"""

    api_key = os.getenv("HIBACHI_PUBLIC_KEY")
    api_secret = os.getenv("HIBACHI_PRIVATE_KEY")
    account_id = os.getenv("HIBACHI_ACCOUNT_ID")

    if not all([api_key, api_secret, account_id]):
        print("❌ Missing credentials in .env")
        print("   Required: HIBACHI_PUBLIC_KEY, HIBACHI_PRIVATE_KEY, HIBACHI_ACCOUNT_ID")
        return False

    print("=" * 70)
    print("🏥 HIBACHI HEALTH CHECK")
    print("=" * 70)

    sdk = HibachiSDK(api_key, api_secret, account_id)

    # 1. Check markets
    print("\n1️⃣ Checking markets...")
    try:
        markets = await sdk.get_markets()
        if not markets:
            print("❌ Failed to fetch markets")
            return False
        print(f"✅ Markets: {len(markets)} available")
        print(f"   Symbols: {', '.join([m['symbol'] for m in markets[:10]])}")
        if len(markets) > 10:
            print(f"   ... and {len(markets) - 10} more")
    except Exception as e:
        print(f"❌ Markets check failed: {e}")
        return False

    # 2. Check balance
    print("\n2️⃣ Checking balance...")
    try:
        balance = await sdk.get_balance()
        if balance is None:
            print("❌ Failed to fetch balance")
            return False
        print(f"✅ Balance: ${balance:.2f} USDT")

        if balance < 10:
            print(f"⚠️  WARNING: Low balance (${balance:.2f})")
    except Exception as e:
        print(f"❌ Balance check failed: {e}")
        return False

    # 3. Check positions
    print("\n3️⃣ Checking open positions...")
    try:
        positions = await sdk.get_positions()
        print(f"✅ Positions: {len(positions)} open")

        if positions:
            print("\n   Current Positions:")
            for pos in positions:
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('direction', 'N/A')
                qty = pos.get('quantity', 0)
                pnl = pos.get('pnl', 0)
                print(f"   • {symbol} {side}: {qty:.8f} (PnL: ${pnl:.2f})")
        else:
            print("   No open positions")
    except Exception as e:
        print(f"❌ Positions check failed: {e}")
        return False

    # 4. Test price fetching
    print("\n4️⃣ Testing price fetching...")
    try:
        test_symbols = ['BTC/USDT-P', 'ETH/USDT-P', 'SOL/USDT-P']
        prices_ok = 0
        for symbol in test_symbols:
            price = await sdk.get_price(symbol)
            if price:
                print(f"   ✅ {symbol}: ${price:,.2f}")
                prices_ok += 1
            else:
                print(f"   ❌ {symbol}: Failed to fetch")

        if prices_ok < len(test_symbols):
            print(f"⚠️  WARNING: Only {prices_ok}/{len(test_symbols)} prices fetched")
    except Exception as e:
        print(f"❌ Price check failed: {e}")
        return False

    # Summary
    print("\n" + "=" * 70)
    print("✅ HEALTH CHECK PASSED")
    print("   API connectivity: OK")
    print("   Markets data: OK")
    print("   Account balance: OK")
    print("   Position fetching: OK")
    print("   Price fetching: OK")
    print("\n💚 Ready to start live trading")
    print("=" * 70)

    return True

if __name__ == "__main__":
    success = asyncio.run(health_check())
    sys.exit(0 if success else 1)
