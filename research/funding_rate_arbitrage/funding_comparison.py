"""
Funding Rate Arbitrage Comparison Tool
=====================================
Compares NATIVE funding rates between Hibachi and Extended DEX
to identify delta-neutral arbitrage opportunities.

Strategy:
- If Hibachi rate > Extended rate: SHORT Hibachi, LONG Extended
- If Extended rate > Hibachi rate: LONG Hibachi, SHORT Extended
- Profit = |rate_diff| * position_size * leverage (collected every 8h)
"""

import asyncio
import aiohttp
import sys
import os
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Extended imports
from x10.perpetual.accounts import StarkPerpetualAccount
from x10.perpetual.configuration import MAINNET_CONFIG
from x10.perpetual.trading_client import PerpetualTradingClient

# Load env
from dotenv import load_dotenv
load_dotenv()

# Constants
HIBACHI_DATA_API_URL = "https://data-api.hibachi.xyz"  # Data API for prices/funding
FUNDING_PERIODS_PER_YEAR = 1095  # 8h intervals = 3/day * 365 days

# Symbol mappings
SYMBOLS = {
    "BTC": {"hibachi": "BTC/USDT-P", "extended": "BTC-USD"},
    "ETH": {"hibachi": "ETH/USDT-P", "extended": "ETH-USD"},
    "SOL": {"hibachi": "SOL/USDT-P", "extended": "SOL-USD"},
}


async def get_hibachi_funding_rates():
    """Fetch NATIVE funding rates from Hibachi via /market/data/prices endpoint."""
    rates = {}

    async with aiohttp.ClientSession() as session:
        for asset, symbols in SYMBOLS.items():
            hibachi_symbol = symbols["hibachi"]
            url = f"{HIBACHI_DATA_API_URL}/market/data/prices?symbol={hibachi_symbol}"

            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Hibachi returns data directly, not wrapped in success/data
                        funding_data = data.get("fundingRateEstimation", {})
                        rate = float(funding_data.get("estimatedFundingRate", 0))
                        next_funding = funding_data.get("nextFundingTimestamp")
                        mark_price = float(data.get("markPrice", 0))

                        rates[asset] = {
                            "rate": rate,
                            "annualized": rate * FUNDING_PERIODS_PER_YEAR * 100,
                            "next_funding_ts": next_funding,
                            "mark_price": mark_price,
                        }
                    else:
                        print(f"  ⚠️ Hibachi {asset}: HTTP {response.status}")
            except Exception as e:
                print(f"  ❌ Hibachi {asset} error: {e}")

    return rates


async def get_extended_funding_rates():
    """Fetch NATIVE funding rates from Extended via SDK."""
    rates = {}

    # Initialize Extended client
    stark_private_key = os.getenv("EXTENDED_STARK_PRIVATE_KEY")
    stark_public_key = os.getenv("EXTENDED_STARK_PUBLIC_KEY")
    api_key = os.getenv("EXTENDED_API_KEY")
    vault = int(os.getenv("EXTENDED_VAULT", "0"))

    stark_account = StarkPerpetualAccount(
        vault=vault,
        private_key=stark_private_key,
        public_key=stark_public_key,
        api_key=api_key,
    )

    trading_client = PerpetualTradingClient(
        endpoint_config=MAINNET_CONFIG,
        stark_account=stark_account
    )

    try:
        for asset, symbols in SYMBOLS.items():
            extended_symbol = symbols["extended"]

            try:
                stats = await trading_client.markets_info.get_market_statistics(market_name=extended_symbol)
                if stats.data:
                    rate = float(stats.data.funding_rate)
                    mark_price = float(stats.data.mark_price) if stats.data.mark_price else 0

                    rates[asset] = {
                        "rate": rate,
                        "annualized": rate * FUNDING_PERIODS_PER_YEAR * 100,
                        "mark_price": mark_price,
                    }
            except Exception as e:
                print(f"  ❌ Extended {asset} error: {e}")
    finally:
        await trading_client.close()

    return rates


def calculate_arbitrage(hibachi_rates: dict, extended_rates: dict):
    """Calculate arbitrage opportunity for each asset."""
    opportunities = []

    for asset in SYMBOLS.keys():
        h_rate = hibachi_rates.get(asset, {})
        e_rate = extended_rates.get(asset, {})

        if not h_rate or not e_rate:
            continue

        h_funding = h_rate.get("rate", 0)
        e_funding = e_rate.get("rate", 0)

        # Calculate spread
        spread = h_funding - e_funding
        spread_annualized = spread * FUNDING_PERIODS_PER_YEAR * 100

        # Determine direction
        if spread > 0:
            # Hibachi rate higher -> SHORT Hibachi (receive), LONG Extended (pay less)
            direction = "SHORT_HIBACHI_LONG_EXTENDED"
            profit_direction = "Receive high rate on Hibachi, pay low rate on Extended"
        else:
            # Extended rate higher -> LONG Hibachi (pay less), SHORT Extended (receive)
            direction = "LONG_HIBACHI_SHORT_EXTENDED"
            profit_direction = "Pay low rate on Hibachi, receive higher rate on Extended"

        opportunities.append({
            "asset": asset,
            "hibachi_rate": h_funding,
            "hibachi_annualized": h_rate.get("annualized", 0),
            "extended_rate": e_funding,
            "extended_annualized": e_rate.get("annualized", 0),
            "spread": abs(spread),
            "spread_annualized": abs(spread_annualized),
            "direction": direction,
            "profit_direction": profit_direction,
            "hibachi_mark": h_rate.get("mark_price", 0),
            "extended_mark": e_rate.get("mark_price", 0),
        })

    # Sort by spread (highest opportunity first)
    opportunities.sort(key=lambda x: x["spread_annualized"], reverse=True)
    return opportunities


async def main():
    print("=" * 80)
    print("🔄 FUNDING RATE ARBITRAGE SCANNER")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Fetch rates from both exchanges
    print("📊 Fetching NATIVE funding rates...")
    print()

    print("  🟡 Hibachi DEX (native /market/data/prices endpoint)...")
    hibachi_rates = await get_hibachi_funding_rates()

    print("  🟣 Extended DEX (native SDK get_market_statistics)...")
    extended_rates = await get_extended_funding_rates()

    print()
    print("=" * 80)
    print("📈 NATIVE FUNDING RATES COMPARISON")
    print("=" * 80)

    print(f"\n{'Asset':<8} {'Hibachi Rate':<18} {'Hibachi Ann.':<14} {'Extended Rate':<18} {'Extended Ann.':<14}")
    print("-" * 80)

    for asset in SYMBOLS.keys():
        h = hibachi_rates.get(asset, {})
        e = extended_rates.get(asset, {})

        h_rate = h.get("rate", 0)
        h_ann = h.get("annualized", 0)
        e_rate = e.get("rate", 0)
        e_ann = e.get("annualized", 0)

        print(f"{asset:<8} {h_rate:<18.8f} {h_ann:>12.2f}%  {e_rate:<18.8f} {e_ann:>12.2f}%")

    print()
    print("=" * 80)
    print("💰 ARBITRAGE OPPORTUNITIES")
    print("=" * 80)

    opportunities = calculate_arbitrage(hibachi_rates, extended_rates)

    for opp in opportunities:
        print()
        print(f"🎯 {opp['asset']}")
        print(f"   Hibachi Rate:  {opp['hibachi_rate']:.8f} ({opp['hibachi_annualized']:+.2f}% annualized)")
        print(f"   Extended Rate: {opp['extended_rate']:.8f} ({opp['extended_annualized']:+.2f}% annualized)")
        print(f"   Spread:        {opp['spread']:.8f} ({opp['spread_annualized']:+.2f}% annualized)")
        print()
        print(f"   Strategy: {opp['direction']}")
        print(f"   Logic: {opp['profit_direction']}")
        print()

        # Profitability analysis
        position_size_usd = 10000
        annual_profit = position_size_usd * (opp['spread_annualized'] / 100)
        daily_profit = annual_profit / 365

        print(f"   📊 Profit Estimate (per $10,000 position):")
        print(f"      Daily:   ${daily_profit:.2f}")
        print(f"      Monthly: ${daily_profit * 30:.2f}")
        print(f"      Annual:  ${annual_profit:.2f}")

        # Risk assessment
        min_viable_spread = 10  # 10% annualized as per Qwen recommendation
        if opp['spread_annualized'] >= min_viable_spread:
            print(f"   ✅ VIABLE: Spread ({opp['spread_annualized']:.2f}%) >= minimum threshold ({min_viable_spread}%)")
        else:
            print(f"   ⚠️  MARGINAL: Spread ({opp['spread_annualized']:.2f}%) < minimum threshold ({min_viable_spread}%)")

    print()
    print("=" * 80)
    print("📋 EXECUTION NOTES")
    print("=" * 80)
    print("""
    1. Funding rates are typically settled every 8 hours
    2. Both positions must be opened simultaneously to maintain delta-neutrality
    3. Position sizes should be equal in USD value on both exchanges
    4. Monitor for funding rate convergence (reduces arbitrage profit)
    5. Account for trading fees on both exchanges when calculating net profit
    6. Slippage on entry/exit will affect realized returns
    7. Liquidation risk if rates move significantly against you
    """)

    print("=" * 80)
    print("🏁 Scan Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
