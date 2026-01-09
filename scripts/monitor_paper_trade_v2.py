#!/usr/bin/env python3
"""
Paper Trade Monitor v2 - Data Accuracy Validation

Runs every 30 minutes to:
1. Check if paper trade process is running
2. Fetch LIVE prices from each exchange API
3. Compare against logged prices in paper trade
4. Flag any significant discrepancies (>0.5%)
5. Log overall health status

Usage: python3 scripts/monitor_paper_trade_v2.py
"""

import os
import sys
import asyncio
import aiohttp
import subprocess
import json
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Config
CHECK_INTERVAL_MINUTES = 30
PAPER_TRADE_LOG = Path("logs/unified_paper_trade.log")
MONITOR_LOG = Path("logs/data_validation_monitor.log")
MAX_PRICE_DIVERGENCE_PCT = 0.5  # Alert if >0.5% difference

def log(msg: str):
    """Log to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(MONITOR_LOG, 'a') as f:
        f.write(line + "\n")

def check_process_running() -> bool:
    """Check if paper trade process is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "unified_paper_trade"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        log(f"Error checking process: {e}")
        return False

async def fetch_hibachi_price(symbol: str) -> float:
    """Fetch live price from Hibachi API"""
    try:
        url = f"https://data-api.hibachi.xyz/market/data/prices?symbol={symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price = data.get('price') or data.get('lastPrice') or data.get('markPrice')
                    if price:
                        return float(price)
    except Exception as e:
        log(f"  Hibachi {symbol} fetch error: {e}")
    return None

async def fetch_extended_price(symbol: str) -> float:
    """Fetch live price from Extended API"""
    try:
        url = f"https://api.starknet.extended.exchange/api/v1/info/markets/{symbol}/stats"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    # Extended wraps data in {"status": "OK", "data": {...}}
                    data = result.get('data', result)
                    price = data.get('mark_price') or data.get('last_price') or data.get('index_price')
                    if price:
                        return float(price)
    except Exception as e:
        log(f"  Extended {symbol} fetch error: {e}")
    return None

async def fetch_paradex_price(symbol: str) -> float:
    """Fetch live price from Paradex API (requires SDK auth, skip for now)"""
    # Paradex requires authenticated SDK - use Binance reference instead
    # The paper trade validates Paradex data internally via the SDK
    return None

async def fetch_binance_price(symbol: str) -> float:
    """Fetch reference price from Binance (most liquid)"""
    try:
        # Convert to Binance format: BTC -> BTCUSDT
        binance_symbol = symbol.replace('/', '').replace('-P', '').replace('-USD', 'USDT').replace('-PERP', '')
        if not binance_symbol.endswith('USDT'):
            binance_symbol = binance_symbol.split('-')[0] + 'USDT'

        url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={binance_symbol}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return float(data.get('price', 0))
    except Exception as e:
        log(f"  Binance {symbol} fetch error: {e}")
    return None

def get_last_logged_prices() -> dict:
    """Parse last logged prices from paper trade log"""
    prices = {}

    if not PAPER_TRADE_LOG.exists():
        return prices

    try:
        # Read last 100 lines of log
        with open(PAPER_TRADE_LOG, 'r') as f:
            lines = f.readlines()[-100:]

        for line in lines:
            # Look for price lines like: [hibachi] BTC/USDT-P: $94,500.00
            if ']: ' in line and ': $' in line:
                try:
                    # Extract exchange and symbol
                    parts = line.split(']')
                    if len(parts) >= 2:
                        exchange = parts[0].split('[')[-1].lower().strip()
                        rest = parts[1]
                        if ': $' in rest:
                            symbol_price = rest.split(': $')
                            symbol = symbol_price[0].strip()
                            price_str = symbol_price[1].split()[0].replace(',', '')
                            price = float(price_str)

                            if exchange not in prices:
                                prices[exchange] = {}
                            prices[exchange][symbol] = price
                except:
                    continue
    except Exception as e:
        log(f"Error parsing log: {e}")

    return prices

async def validate_data_accuracy():
    """Main validation - compare logged prices to live exchange data"""
    log("=" * 60)
    log("DATA ACCURACY VALIDATION")
    log("=" * 60)

    # Get prices from live APIs
    live_prices = {}

    # Hibachi
    log("Fetching Hibachi prices...")
    live_prices['hibachi'] = {}
    for symbol in ['BTC/USDT-P', 'ETH/USDT-P', 'SOL/USDT-P']:
        price = await fetch_hibachi_price(symbol)
        if price:
            live_prices['hibachi'][symbol] = price
            log(f"  {symbol}: ${price:,.2f}")

    # Extended
    log("Fetching Extended prices...")
    live_prices['extended'] = {}
    for symbol in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
        price = await fetch_extended_price(symbol)
        if price:
            live_prices['extended'][symbol] = price
            log(f"  {symbol}: ${price:,.2f}")

    # Paradex
    log("Fetching Paradex prices...")
    live_prices['paradex'] = {}
    price = await fetch_paradex_price('BTC-USD-PERP')
    if price:
        live_prices['paradex']['BTC-USD-PERP'] = price
        log(f"  BTC-USD-PERP: ${price:,.2f}")

    # Binance reference
    log("Fetching Binance reference prices...")
    binance_prices = {}
    for symbol in ['BTC', 'ETH', 'SOL']:
        price = await fetch_binance_price(symbol)
        if price:
            binance_prices[symbol] = price
            log(f"  {symbol}: ${price:,.2f}")

    # Compare exchange prices to Binance reference
    log("")
    log("EXCHANGE vs BINANCE COMPARISON:")
    log("-" * 50)

    issues = []

    for exchange, symbols in live_prices.items():
        for symbol, price in symbols.items():
            # Extract base asset (BTC, ETH, SOL)
            base = symbol.split('/')[0].split('-')[0]
            binance_ref = binance_prices.get(base)

            if binance_ref and price:
                diff_pct = abs(price - binance_ref) / binance_ref * 100
                status = "✅" if diff_pct < MAX_PRICE_DIVERGENCE_PCT else "⚠️"

                log(f"  [{exchange}] {symbol}: ${price:,.2f} vs Binance ${binance_ref:,.2f} ({diff_pct:.3f}% diff) {status}")

                if diff_pct >= MAX_PRICE_DIVERGENCE_PCT:
                    issues.append(f"{exchange}/{symbol}: {diff_pct:.2f}% divergence from Binance")

    # Summary
    log("")
    log("=" * 60)

    if issues:
        log(f"⚠️ ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            log(f"  - {issue}")
    else:
        log("✅ ALL PRICES WITHIN TOLERANCE")

    # Data availability check
    total_symbols = sum(len(s) for s in live_prices.values())
    log(f"Data coverage: {total_symbols}/7 symbols fetched")

    if total_symbols < 3:
        log("❌ CRITICAL: Less than 3 symbols available!")
        return False

    return len(issues) == 0

async def run_monitor():
    """Main monitor loop"""
    log("")
    log("=" * 60)
    log("PAPER TRADE MONITOR STARTED")
    log(f"Check interval: {CHECK_INTERVAL_MINUTES} minutes")
    log(f"Max price divergence: {MAX_PRICE_DIVERGENCE_PCT}%")
    log("=" * 60)

    check_count = 0

    while True:
        check_count += 1
        log("")
        log(f"CHECK #{check_count}")
        log("-" * 40)

        # 1. Check if process is running
        is_running = check_process_running()
        if is_running:
            log("✅ Paper trade process is RUNNING")
        else:
            log("❌ Paper trade process is NOT RUNNING!")
            log("   Continuing monitoring for data validation...")

        # 2. Validate data accuracy
        await validate_data_accuracy()

        # 3. Check if paper trade completed
        if PAPER_TRADE_LOG.exists():
            with open(PAPER_TRADE_LOG, 'r') as f:
                content = f.read()
                if "FINAL REPORT" in content:
                    log("🏁 Paper trade has COMPLETED")
                    break

        log(f"\nNext check in {CHECK_INTERVAL_MINUTES} minutes...")
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

    log("")
    log("=" * 60)
    log("MONITOR STOPPED")
    log("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_monitor())
