"""
VWAP Calculation Utilities
Session VWAP with midnight UTC reset
"""

import requests
from datetime import datetime, timezone
from typing import Optional


def calculate_session_vwap(symbol: str) -> Optional[float]:
    """
    Calculate Session VWAP (resets at midnight UTC)
    Uses Pacifica 15m candles

    Formula: VWAP = Sum(Typical_Price × Volume) / Sum(Volume)
    Typical_Price = (High + Low + Close) / 3

    Args:
        symbol: Trading symbol (e.g., "SOL", "BTC")

    Returns:
        VWAP value or None if calculation fails
    """
    try:
        # Get midnight UTC today
        now_utc = datetime.now(timezone.utc)
        midnight_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        # Convert to milliseconds for Pacifica API
        start_ms = int(midnight_utc.timestamp() * 1000)
        end_ms = int(now_utc.timestamp() * 1000)

        # Fetch 15m candles from midnight to now
        url = f"https://api.pacifica.fi/api/v1/kline?symbol={symbol}&interval=15m&start_time={start_ms}&end_time={end_ms}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"⚠️  VWAP API error for {symbol}: HTTP {response.status_code}")
            return None

        data = response.json()

        if not data.get('success'):
            print(f"⚠️  VWAP API error for {symbol}: {data}")
            return None

        candles = data.get('data', [])

        if not candles:
            print(f"⚠️  No candles for {symbol} since midnight UTC")
            return None

        # Calculate VWAP using typical price
        cumulative_pv = 0.0
        cumulative_volume = 0.0

        for candle in candles:
            high = float(candle['h'])
            low = float(candle['l'])
            close = float(candle['c'])
            volume = float(candle['v'])

            # Typical price = (H + L + C) / 3
            typical_price = (high + low + close) / 3

            cumulative_pv += typical_price * volume
            cumulative_volume += volume

        if cumulative_volume == 0:
            print(f"⚠️  Zero volume for {symbol}")
            return None

        vwap = cumulative_pv / cumulative_volume

        # Log calculation details
        hours_since_midnight = (now_utc - midnight_utc).total_seconds() / 3600
        print(f"📊 {symbol} VWAP: ${vwap:.2f} ({len(candles)} candles, {hours_since_midnight:.1f}h)")

        return vwap

    except Exception as e:
        print(f"❌ VWAP calculation error for {symbol}: {e}")
        return None


def get_current_price_from_orderbook(symbol: str) -> Optional[float]:
    """
    Get current mid price from Pacifica orderbook

    Args:
        symbol: Trading symbol

    Returns:
        Mid price or None if fails
    """
    try:
        url = f"https://api.pacifica.fi/api/v1/book?symbol={symbol}"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()

        if not data.get('success'):
            return None

        book_data = data.get('data', {})

        if 'l' not in book_data or len(book_data['l']) < 2:
            return None

        bids = book_data['l'][0]
        asks = book_data['l'][1]

        if not bids or not asks:
            return None

        best_bid = float(bids[0]['p'])
        best_ask = float(asks[0]['p'])
        mid_price = (best_bid + best_ask) / 2

        return mid_price

    except Exception as e:
        print(f"❌ Price fetch error for {symbol}: {e}")
        return None


if __name__ == "__main__":
    # Test VWAP calculation
    test_symbols = ["SOL", "BTC", "ETH", "PENGU", "XPL", "ASTER"]

    print("=" * 70)
    print("TESTING SESSION VWAP CALCULATION")
    print("=" * 70)

    for symbol in test_symbols:
        print(f"\n[{symbol}]")
        vwap = calculate_session_vwap(symbol)
        current_price = get_current_price_from_orderbook(symbol)

        if vwap and current_price:
            diff = current_price - vwap
            diff_pct = (diff / vwap) * 100

            if current_price > vwap:
                signal = f"🟢 BULLISH (+{diff_pct:.2f}%)"
            else:
                signal = f"🔴 BEARISH ({diff_pct:.2f}%)"

            print(f"  Current: ${current_price:.4f}")
            print(f"  VWAP:    ${vwap:.4f}")
            print(f"  Signal:  {signal}")
        else:
            print(f"  ✗ Failed to calculate")

    print("\n" + "=" * 70)
