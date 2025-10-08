#!/usr/bin/env python3
"""
Minimal test - Try to place order working around SDK bugs
"""

import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

async def test_order():
    import lighter

    print("="*60)
    print("MINIMAL LIGHTER ORDER TEST")
    print("="*60)

    # Initialize client
    client = lighter.SignerClient(
        url="https://mainnet.zklighter.elliot.ai",
        private_key=os.getenv("LIGHTER_API_KEY_PRIVATE"),
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX")),
    )

    print(f"\n✅ Client initialized")
    print(f"Account Index: {os.getenv('LIGHTER_ACCOUNT_INDEX')}")
    print(f"API Key Index: {os.getenv('LIGHTER_API_KEY_INDEX')}")

    # Get account info first
    api_client = lighter.ApiClient(configuration=lighter.Configuration(host="https://mainnet.zklighter.elliot.ai"))
    account_api = lighter.AccountApi(api_client)

    account = await account_api.account(
        by="index",
        value=str(os.getenv("LIGHTER_ACCOUNT_INDEX"))
    )

    if hasattr(account, 'accounts') and account.accounts:
        acc = account.accounts[0]
        print(f"\n💰 Balance: ${float(acc.available_balance):.2f}")

    # Try IOC order (immediate or cancel - like market order)
    # This should execute immediately and not need expiry
    print("\n📝 Creating IOC order for SOL...")
    print("   Market: SOL (market_id=2)")
    print("   Size: 0.050 SOL (minimum)")
    print("   Type: LIMIT with IOC (acts like market)")

    current_time = int(time.time())

    try:
        # Use create_market_order which should be simpler
        result = await client.create_market_order(
            market_index=2,  # SOL
            client_order_index=int(time.time() * 1000) % 1000000,
            base_amount=50,  # 0.050 SOL (50 with 3 decimals)
            avg_execution_price=250000,  # High price $250 to ensure fill
            is_ask=False,  # BUY
            reduce_only=False
        )

        print(f"\n✅ Result: {result}")
        print(f"Type: {type(result)}")

        if result:
            tx, tx_hash, error = result
            if error:
                print(f"❌ Error: {error}")
            else:
                print(f"✅ Transaction: {tx}")
                print(f"✅ Hash: {tx_hash}")

    except AttributeError as e:
        # SDK wrapper bug - but order might have gone through
        print(f"\n⚠️  SDK wrapper bug (expected): {e}")
        print("Waiting 3 seconds then checking if order executed...")

        await asyncio.sleep(3)

        # Check positions
        account = await account_api.account(
            by="index",
            value=str(os.getenv("LIGHTER_ACCOUNT_INDEX"))
        )

        if hasattr(account, 'accounts') and account.accounts:
            acc = account.accounts[0]
            print(f"\n💰 New Balance: ${float(acc.available_balance):.2f}")

            if hasattr(acc, 'positions'):
                sol_pos = [p for p in acc.positions if p.market_id == 2 and float(p.position) != 0]
                if sol_pos:
                    pos = sol_pos[0]
                    print(f"\n🎉 ORDER EXECUTED DESPITE SDK BUG!")
                    print(f"   Size: {pos.position} SOL")
                    print(f"   Entry: ${pos.avg_entry_price}")
                    print(f"   Value: ${pos.position_value}")
                else:
                    print("\n❌ No SOL position - order failed")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    await api_client.close()
    await client.close()

    print("\n" + "="*60)

asyncio.run(test_order())
