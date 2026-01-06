#!/usr/bin/env python3
"""
Smart Volume Farming on Paradex
- Checks spread before trading, skips if too wide
- Auto-stops on loss limit
- Works with any symbol
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
SYMBOL = "BTC-USD-PERP"  # BTC has tightest spread (0.0003%)
TRADE_SIZE = Decimal("0.0001")  # 0.0001 BTC ~ $8.80
MAX_SPREAD_PCT = 0.01  # Skip if spread > 0.01%
MAX_LOSS = 1.0  # Stop if we lose $1
DURATION_SECONDS = 120  # 2 min test

paradex = ParadexSubkey(
    env='prod',
    l2_private_key=os.getenv('PARADEX_PRIVATE_SUBKEY'),
    l2_address=os.getenv('PARADEX_ACCOUNT_ADDRESS'),
)

def get_spread():
    """Get current bid/ask/spread"""
    bbo = paradex.api_client.fetch_bbo(market=SYMBOL)
    bid = float(bbo.get('bid', 0))
    ask = float(bbo.get('ask', 0))
    spread_pct = ((ask - bid) / bid) * 100 if bid > 0 else 999
    return bid, ask, spread_pct

def place_order(side):
    order = Order(
        market=SYMBOL,
        order_type=OrderType.Market,
        order_side=OrderSide.Buy if side == "BUY" else OrderSide.Sell,
        size=TRADE_SIZE,
    )
    return paradex.api_client.submit_order(order)

# Get starting balance and price
start_balance = float(paradex.api_client.fetch_account_summary().account_value)
bid, ask, spread_pct = get_spread()
trade_value = float(TRADE_SIZE) * bid

print(f"Starting balance: ${start_balance:.2f}")
print(f"Max loss limit: ${MAX_LOSS}")
print(f"Symbol: {SYMBOL}")
print(f"Trade size: {TRADE_SIZE} BTC (~${trade_value:.2f})")
print(f"Max spread: {MAX_SPREAD_PCT}%")
print(f"Current spread: {spread_pct:.4f}%")
print("=" * 60)

start_time = datetime.now()
end_time = start_time + timedelta(seconds=DURATION_SECONDS)
round_trips = 0
skipped = 0
total_volume = 0.0

while datetime.now() < end_time:
    try:
        # Check spread before trading
        bid, ask, spread_pct = get_spread()

        if spread_pct > MAX_SPREAD_PCT:
            skipped += 1
            if skipped % 10 == 0:
                print(f"Skipped {skipped} (spread {spread_pct:.4f}% > {MAX_SPREAD_PCT}%)")
            time.sleep(0.2)
            continue

        # Open long
        place_order("BUY")
        time.sleep(0.03)

        # Close long
        place_order("SELL")

        round_trips += 1
        trade_value = float(TRADE_SIZE) * bid
        total_volume += trade_value * 2  # buy + sell

        # Check PnL every 10 round trips
        if round_trips % 10 == 0:
            current_balance = float(paradex.api_client.fetch_account_summary().account_value)
            pnl = current_balance - start_balance
            elapsed = (datetime.now() - start_time).total_seconds()

            print(f"RT#{round_trips} | PnL: ${pnl:+.3f} | Vol: ${total_volume:,.0f} | Spread: {spread_pct:.4f}% | Skip: {skipped}")

            # STOP if losing too much
            if pnl < -MAX_LOSS:
                print(f"\n⚠️  STOP: Loss limit reached (${pnl:.2f})")
                break

        time.sleep(0.05)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)

# Final stats
final_balance = float(paradex.api_client.fetch_account_summary().account_value)
pnl = final_balance - start_balance
elapsed = (datetime.now() - start_time).total_seconds()

print()
print("=" * 60)
print("FINAL RESULTS")
print("=" * 60)
print(f"Duration: {elapsed:.0f}s")
print(f"Round trips: {round_trips}")
print(f"Skipped (spread too wide): {skipped}")
print(f"Total trades: {round_trips * 2}")
print(f"Volume: ${total_volume:,.0f}")
print(f"Start: ${start_balance:.2f} -> End: ${final_balance:.2f}")
print(f"PnL: ${pnl:+.3f}")
if round_trips > 0:
    print(f"Cost per RT: ${abs(pnl)/round_trips:.5f}")
    print(f"Cost rate: {abs(pnl)/total_volume*100:.4f}% of volume")
