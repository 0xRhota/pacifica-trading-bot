#!/usr/bin/env python3
"""
Paradex Volume Farming - 5 min test on LIT-USD-PERP
Strategy: Rapid round trips (long->close->short->close)
"""

import asyncio
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


class ParadexVolumeFarmer:
    def __init__(
        self,
        symbol: str = "LIT-USD-PERP",
        trade_size: float = 20.0,  # Size in contracts (LIT)
        duration_minutes: int = 5,
    ):
        self.symbol = symbol
        self.trade_size = Decimal(str(trade_size))
        self.duration_minutes = duration_minutes

        # Stats
        self.total_volume = 0.0
        self.total_trades = 0
        self.start_time = None
        self.start_balance = 0.0

        self.paradex = None

    def initialize(self):
        """Initialize Paradex client"""
        print("Initializing Paradex...")

        self.paradex = ParadexSubkey(
            env='prod',
            l2_private_key=os.getenv('PARADEX_PRIVATE_SUBKEY'),
            l2_address=os.getenv('PARADEX_ACCOUNT_ADDRESS'),
        )

        # Get starting balance
        acc = self.paradex.api_client.fetch_account_summary()
        self.start_balance = float(acc.account_value)
        print(f"Starting balance: ${self.start_balance:.2f}")

        # Get current price
        bbo = self.paradex.api_client.fetch_bbo(market=self.symbol)
        price = float(bbo.get('bid', 0))
        print(f"{self.symbol} price: ${price:.4f}")
        print(f"Trade size: {self.trade_size} contracts (~${float(self.trade_size) * price:.2f})")

        return True

    def place_market_order(self, side: str) -> dict:
        """Place a market order"""
        order = Order(
            market=self.symbol,
            order_type=OrderType.Market,
            order_side=OrderSide.Buy if side == "BUY" else OrderSide.Sell,
            size=self.trade_size,
        )
        return self.paradex.api_client.submit_order(order)

    def execute_round_trip(self) -> dict:
        """Execute one round trip: open and close position"""
        try:
            # Open LONG
            open_result = self.place_market_order("BUY")
            if open_result.get('status') not in ['NEW', 'FILLED']:
                return {'success': False, 'error': f"Open failed: {open_result}"}

            # Minimal pause - just enough for order to register
            time.sleep(0.05)

            # Close LONG (sell)
            close_result = self.place_market_order("SELL")
            if close_result.get('status') not in ['NEW', 'FILLED']:
                return {'success': False, 'error': f"Close failed: {close_result}"}

            return {'success': True, 'trades': 2}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_current_price(self) -> float:
        """Get current price"""
        bbo = self.paradex.api_client.fetch_bbo(market=self.symbol)
        return float(bbo.get('bid', 0))

    def run(self):
        """Main farming loop"""
        print("=" * 60)
        print("PARADEX VOLUME FARMING - ZERO FEES")
        print("=" * 60)
        print(f"Symbol: {self.symbol}")
        print(f"Trade size: {self.trade_size} contracts")
        print(f"Duration: {self.duration_minutes} minutes")
        print("=" * 60)

        if not self.initialize():
            return

        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(minutes=self.duration_minutes)

        round_trip_count = 0
        price = self.get_current_price()

        print(f"\nStarting at {self.start_time.strftime('%H:%M:%S')}...")
        print(f"End time: {end_time.strftime('%H:%M:%S')}")
        print()

        while datetime.now() < end_time:
            result = self.execute_round_trip()

            if result.get('success'):
                round_trip_count += 1
                # Volume = size * price * 2 (buy + sell)
                trade_volume = float(self.trade_size) * price * 2
                self.total_volume += trade_volume
                self.total_trades += 2

                elapsed = (datetime.now() - self.start_time).total_seconds()
                print(
                    f"RT#{round_trip_count} | "
                    f"Vol: ${self.total_volume:,.0f} | "
                    f"Trades: {self.total_trades} | "
                    f"Time: {elapsed:.0f}s"
                )
            else:
                print(f"ERROR: {result.get('error')}")
                time.sleep(1)

            # Minimal delay - maximize throughput (1500 req/min = 25/sec)
            # Each round trip = 2 orders, so ~12 round trips/sec max
            time.sleep(0.1)

            # Update price every 50 round trips
            if round_trip_count % 50 == 0:
                price = self.get_current_price()

        # Final stats
        elapsed = (datetime.now() - self.start_time).total_seconds()
        acc = self.paradex.api_client.fetch_account_summary()
        final_balance = float(acc.account_value)

        print()
        print("=" * 60)
        print("FINAL STATS")
        print("=" * 60)
        print(f"Duration: {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
        print(f"Round trips: {round_trip_count}")
        print(f"Total trades: {self.total_trades}")
        print(f"Total volume: ${self.total_volume:,.2f}")
        print(f"Start balance: ${self.start_balance:.2f}")
        print(f"End balance: ${final_balance:.2f}")
        print(f"P/L: ${final_balance - self.start_balance:.2f}")
        print(f"Volume/minute: ${self.total_volume / (elapsed/60):,.0f}")
        print("=" * 60)


def main():
    farmer = ParadexVolumeFarmer(
        symbol="LIT-USD-PERP",
        trade_size=20.0,  # 20 LIT ~ $50
        duration_minutes=5,
    )
    farmer.run()


if __name__ == "__main__":
    main()
