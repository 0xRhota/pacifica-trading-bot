#!/usr/bin/env python3
"""
Safe ETH Volume Farming on Paradex
- Uses ETH-USD-PERP (0.006% spread vs LIT's 3%+)
- Auto-stops if losses exceed limit
- Live PnL monitoring
"""

import os
import sys
import time
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from paradex_py import ParadexSubkey
from paradex_py.common.order import Order, OrderType, OrderSide

# Config
SYMBOL = "ETH-USD-PERP"
TRADE_SIZE = Decimal("0.01")  # 0.01 ETH ~ $30
MAX_LOSS = 2.0  # Stop if we lose $2
DURATION_SECONDS = 120  # 2 min test

paradex = ParadexSubkey(
    env='prod',
    l2_private_key=os.getenv('PARADEX_PRIVATE_SUBKEY'),
    l2_address=os.getenv('PARADEX_ACCOUNT_ADDRESS'),
)

# Get starting balance
start_balance = float(paradex.api_client.fetch_account_summary().account_value)
print(f"Starting balance: ${start_balance:.2f}")
print(f"Max loss limit: ${MAX_LOSS}")
print(f"Symbol: {SYMBOL}, Size: {TRADE_SIZE} ETH (~${float(TRADE_SIZE) * 2980:.0f})")
print("=" * 50)

start_time = datetime.now()
end_time = start_time + timedelta(seconds=DURATION_SECONDS)
round_trips = 0
total_volume = 0.0

def place_order(side):
    order = Order(
        market=SYMBOL,
        order_type=OrderType.Market,
        order_side=OrderSide.Buy if side == "BUY" else OrderSide.Sell,
        size=TRADE_SIZE,
    )
    return paradex.api_client.submit_order(order)

while datetime.now() < end_time:
    try:
        # Open long
        place_order("BUY")
        time.sleep(0.05)

        # Close long
        place_order("SELL")

        round_trips += 1

        # Check PnL every 5 round trips
        if round_trips % 5 == 0:
            current_balance = float(paradex.api_client.fetch_account_summary().account_value)
            pnl = current_balance - start_balance
            bbo = paradex.api_client.fetch_bbo(market=SYMBOL)
            price = float(bbo.get('bid', 0))
            total_volume = round_trips * 2 * float(TRADE_SIZE) * price

            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"RT#{round_trips} | PnL: ${pnl:+.2f} | Vol: ${total_volume:,.0f} | Time: {elapsed:.0f}s")

            # STOP if losing too much
            if pnl < -MAX_LOSS:
                print(f"\n⚠️  STOP: Loss limit reached (${pnl:.2f})")
                break

        time.sleep(0.1)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)

# Final stats
final_balance = float(paradex.api_client.fetch_account_summary().account_value)
pnl = final_balance - start_balance
elapsed = (datetime.now() - start_time).total_seconds()

print()
print("=" * 50)
print("FINAL RESULTS")
print("=" * 50)
print(f"Duration: {elapsed:.0f}s")
print(f"Round trips: {round_trips}")
print(f"Total trades: {round_trips * 2}")
print(f"Volume: ${total_volume:,.0f}")
print(f"Start: ${start_balance:.2f} -> End: ${final_balance:.2f}")
print(f"PnL: ${pnl:+.2f}")
if round_trips > 0:
    print(f"Cost per RT: ${abs(pnl)/round_trips:.4f}")
