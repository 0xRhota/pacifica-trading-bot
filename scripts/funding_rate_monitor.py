#!/usr/bin/env python3
"""
Funding Rate Monitor
====================
Monitors funding rate spreads across exchanges and alerts when opportunities arise.

Public APIs used (no auth required):
- Hibachi: data-api.hibachi.xyz/market/data/prices
- Pacifica: api.pacifica.fi/api/v1/info

Usage:
    python3 scripts/funding_rate_monitor.py                    # Run once
    python3 scripts/funding_rate_monitor.py --continuous       # Run every 30 min
    python3 scripts/funding_rate_monitor.py --threshold 15     # Alert at 15% spread
"""

import asyncio
import aiohttp
import argparse
from datetime import datetime
from pathlib import Path

# Config
DEFAULT_THRESHOLD_PCT = 10.0  # Alert when annualized spread > 10%
CHECK_INTERVAL_MINUTES = 30
LOG_FILE = Path("logs/funding_rate_monitor.log")


def log(msg: str):
    """Log to console and file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


async def fetch_hibachi_funding(symbol: str = "BTC/USDT-P") -> dict:
    """Fetch funding rate from Hibachi"""
    try:
        url = f"https://data-api.hibachi.xyz/market/data/prices?symbol={symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    fr_data = data.get("fundingRateEstimation", {})
                    rate = float(fr_data.get("estimatedFundingRate", 0))
                    next_ts = fr_data.get("nextFundingTimestamp", 0)
                    return {
                        "exchange": "Hibachi",
                        "symbol": symbol.split("/")[0],
                        "rate": rate,
                        "rate_8h_pct": rate * 100,
                        "rate_annualized_pct": rate * 100 * 1095,  # 8h periods per year
                        "next_funding": datetime.fromtimestamp(next_ts) if next_ts else None
                    }
    except Exception as e:
        log(f"Error fetching Hibachi: {e}")
    return None


async def fetch_pacifica_funding() -> list:
    """Fetch all funding rates from Pacifica"""
    results = []
    try:
        url = "https://api.pacifica.fi/api/v1/info"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for market in data.get("data", []):
                        symbol = market.get("symbol")
                        rate = float(market.get("funding_rate", 0))
                        results.append({
                            "exchange": "Pacifica",
                            "symbol": symbol,
                            "rate": rate,
                            "rate_8h_pct": rate * 100,
                            "rate_annualized_pct": rate * 100 * 1095
                        })
    except Exception as e:
        log(f"Error fetching Pacifica: {e}")
    return results


def calculate_spread(rate1: float, rate2: float) -> float:
    """Calculate spread between two funding rates (annualized %)"""
    return abs(rate1 - rate2) * 100 * 1095


async def check_funding_rates(threshold_pct: float):
    """Check funding rates and alert on opportunities"""
    log("=" * 60)
    log("FUNDING RATE CHECK")
    log("=" * 60)

    # Fetch from all exchanges
    hibachi_btc = await fetch_hibachi_funding("BTC/USDT-P")
    hibachi_eth = await fetch_hibachi_funding("ETH/USDT-P")
    hibachi_sol = await fetch_hibachi_funding("SOL/USDT-P")
    pacifica_rates = await fetch_pacifica_funding()

    # Build rate lookup
    rates = {}

    for data in [hibachi_btc, hibachi_eth, hibachi_sol]:
        if data:
            key = f"{data['exchange']}:{data['symbol']}"
            rates[key] = data
            log(f"  {data['exchange']:10} {data['symbol']:4}: {data['rate_8h_pct']:+.4f}% (8h) = {data['rate_annualized_pct']:+.1f}% ann")

    for data in pacifica_rates:
        if data["symbol"] in ["BTC", "ETH", "SOL"]:
            key = f"{data['exchange']}:{data['symbol']}"
            rates[key] = data
            log(f"  {data['exchange']:10} {data['symbol']:4}: {data['rate_8h_pct']:+.4f}% (8h) = {data['rate_annualized_pct']:+.1f}% ann")

    # Check spreads between exchanges
    log("")
    log("CROSS-EXCHANGE SPREADS:")
    log("-" * 60)

    opportunities = []

    for symbol in ["BTC", "ETH", "SOL"]:
        hibachi_key = f"Hibachi:{symbol}"
        pacifica_key = f"Pacifica:{symbol}"

        if hibachi_key in rates and pacifica_key in rates:
            h_rate = rates[hibachi_key]["rate"]
            p_rate = rates[pacifica_key]["rate"]
            spread = calculate_spread(h_rate, p_rate)

            # Determine arb direction
            if h_rate < p_rate:
                direction = "LONG Hibachi / SHORT Pacifica"
            else:
                direction = "SHORT Hibachi / LONG Pacifica"

            status = "***" if spread >= threshold_pct else ""
            log(f"  {symbol}: {spread:+.1f}% spread {status}")

            if spread >= threshold_pct:
                opportunities.append({
                    "symbol": symbol,
                    "spread_pct": spread,
                    "direction": direction,
                    "hibachi_rate": h_rate,
                    "pacifica_rate": p_rate
                })

    # Summary
    log("")
    log("=" * 60)

    if opportunities:
        log(f"*** {len(opportunities)} OPPORTUNITY(IES) FOUND! (>{threshold_pct}% spread)")
        for opp in opportunities:
            log(f"  {opp['symbol']}: {opp['spread_pct']:.1f}% ann - {opp['direction']}")
            log(f"    Hibachi: {opp['hibachi_rate']*100:.4f}%/8h, Pacifica: {opp['pacifica_rate']*100:.4f}%/8h")
    else:
        log(f"No opportunities above {threshold_pct}% threshold")

    log("=" * 60)
    return opportunities


async def run_continuous(threshold_pct: float):
    """Run monitor continuously"""
    log("")
    log("FUNDING RATE MONITOR - CONTINUOUS MODE")
    log(f"Threshold: {threshold_pct}% annualized spread")
    log(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    log("")

    while True:
        await check_funding_rates(threshold_pct)
        log(f"\nNext check in {CHECK_INTERVAL_MINUTES} minutes...")
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)


async def main():
    parser = argparse.ArgumentParser(description="Funding Rate Monitor")
    parser.add_argument("--continuous", action="store_true", help="Run continuously")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD_PCT,
                        help=f"Alert threshold in annualized %% (default: {DEFAULT_THRESHOLD_PCT})")
    args = parser.parse_args()

    if args.continuous:
        await run_continuous(args.threshold)
    else:
        await check_funding_rates(args.threshold)


if __name__ == "__main__":
    asyncio.run(main())
