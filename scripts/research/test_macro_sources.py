"""
Compare macro market data from multiple sources
- Deep42 (Cambrian): AI-powered market analysis
- CoinGecko: Global market metrics
- Fear & Greed Index: Market sentiment indicator
"""

import requests
import json
from datetime import datetime

def get_deep42_sentiment():
    """Get Deep42 market analysis"""
    url = "https://deep42.cambrian.network/api/v1/deep42/agents/deep42"
    headers = {
        "X-API-KEY": "doug.ZbEScx8M4zlf7kDn",
        "Content-Type": "application/json"
    }
    params = {
        "question": "What is the current state of the cryptocurrency market? Include: 1) Overall market sentiment 2) Any upcoming catalysts or events this week 3) Short-term and mid-term outlook for Bitcoin and major altcoins"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        if response.status_code == 200:
            data = response.json()
            return data.get("answer"), data.get("chat_id")
        else:
            return None, None
    except Exception as e:
        print(f"Deep42 error: {e}")
        return None, None

def get_coingecko_global():
    """Get CoinGecko global market data"""
    try:
        response = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
        if response.status_code == 200:
            return response.json()["data"]
        return None
    except Exception as e:
        print(f"CoinGecko error: {e}")
        return None

def get_fear_greed_index():
    """Get Fear & Greed Index"""
    try:
        response = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
        if response.status_code == 200:
            data = response.json()["data"][0]
            return {
                "value": int(data["value"]),
                "classification": data["value_classification"],
                "timestamp": data["timestamp"]
            }
        return None
    except Exception as e:
        print(f"Fear & Greed error: {e}")
        return None

def format_number(num):
    """Format large numbers with commas"""
    return f"{num:,.0f}"

if __name__ == "__main__":
    print("=" * 80)
    print("MACRO MARKET DATA COMPARISON")
    print("=" * 80)
    print()

    # 1. Deep42 Analysis
    print("1. DEEP42 (CAMBRIAN) - AI-Powered Market Analysis")
    print("-" * 80)
    deep42_answer, chat_id = get_deep42_sentiment()
    if deep42_answer:
        print(deep42_answer)
    else:
        print("❌ Failed to fetch Deep42 data")
    print()
    print()

    # 2. CoinGecko Global Metrics
    print("2. COINGECKO - Global Market Metrics")
    print("-" * 80)
    cg_data = get_coingecko_global()
    if cg_data:
        print(f"Total Market Cap: ${format_number(cg_data['total_market_cap']['usd'])}")
        print(f"Total 24h Volume: ${format_number(cg_data['total_volume']['usd'])}")
        print(f"BTC Dominance: {cg_data['market_cap_percentage']['btc']:.2f}%")
        print(f"ETH Dominance: {cg_data['market_cap_percentage']['eth']:.2f}%")
        print(f"Market Cap Change 24h: {cg_data['market_cap_change_percentage_24h_usd']:.2f}%")
        print(f"Active Cryptocurrencies: {format_number(cg_data['active_cryptocurrencies'])}")

        # Interpret market cap change
        mc_change = cg_data['market_cap_change_percentage_24h_usd']
        if mc_change > 2:
            sentiment = "🟢 BULLISH"
        elif mc_change > 0:
            sentiment = "🟡 SLIGHTLY BULLISH"
        elif mc_change > -2:
            sentiment = "🟠 SLIGHTLY BEARISH"
        else:
            sentiment = "🔴 BEARISH"
        print(f"Sentiment (based on 24h change): {sentiment}")
    else:
        print("❌ Failed to fetch CoinGecko data")
    print()
    print()

    # 3. Fear & Greed Index
    print("3. FEAR & GREED INDEX - Market Sentiment")
    print("-" * 80)
    fg_data = get_fear_greed_index()
    if fg_data:
        value = fg_data["value"]
        classification = fg_data["classification"]

        # Display with emoji
        if value >= 75:
            emoji = "🔥"
        elif value >= 55:
            emoji = "😊"
        elif value >= 45:
            emoji = "😐"
        elif value >= 25:
            emoji = "😰"
        else:
            emoji = "😱"

        print(f"Current Index: {value}/100 {emoji}")
        print(f"Classification: {classification.upper()}")
        print()
        print("Scale:")
        print("  0-24: Extreme Fear 😱")
        print("  25-44: Fear 😰")
        print("  45-54: Neutral 😐")
        print("  55-74: Greed 😊")
        print("  75-100: Extreme Greed 🔥")
    else:
        print("❌ Failed to fetch Fear & Greed Index")
    print()
    print()

    # Summary Comparison
    print("4. COMPARISON SUMMARY")
    print("-" * 80)
    print()
    print("Deep42 Strengths:")
    print("  ✅ AI-powered analysis with context and reasoning")
    print("  ✅ Provides upcoming catalysts and events")
    print("  ✅ Short-term AND mid-term outlook for specific assets")
    print("  ✅ Sentiment analysis based on on-chain and social data")
    print("  ✅ Actionable insights (not just numbers)")
    print()
    print("CoinGecko Strengths:")
    print("  ✅ Real-time global market metrics")
    print("  ✅ BTC/ETH dominance (useful for altcoin season timing)")
    print("  ✅ 24h volume (liquidity indicator)")
    print("  ✅ Free, no auth required")
    print()
    print("Fear & Greed Index Strengths:")
    print("  ✅ Single number (0-100) sentiment score")
    print("  ✅ Simple to interpret")
    print("  ✅ Historical data available")
    print("  ✅ Free, no auth required")
    print()
    print()
    print("RECOMMENDATION FOR LLM BOT:")
    print("-" * 80)
    print("Use DEEP42 as primary macro context source:")
    print("  - Provides the 'why' behind market moves")
    print("  - Explains catalysts and events")
    print("  - Gives asset-specific outlook")
    print()
    print("Supplement with CoinGecko + Fear & Greed for quick numbers:")
    print("  - Market cap change (is market growing/shrinking?)")
    print("  - BTC dominance (altcoin season indicator)")
    print("  - Fear & Greed score (contrarian signal)")
    print()
    print("=" * 80)
