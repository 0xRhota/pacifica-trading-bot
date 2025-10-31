"""
Example: LLM Trading Bot with Macro Context Integration

This shows how macro context is integrated into the prompt on every decision cycle
"""

import time
from datetime import datetime
from macro_context_fetcher import MacroContextFetcher

# Simulate bot components
class MockMarketData:
    """Mock market data for example"""
    def get_all_markets(self):
        return {
            "SOL": {"price": 195.40, "volume_24h": 2.3e9, "funding_rate": 0.0125, "oi": 8055793},
            "BTC": {"price": 110885, "volume_24h": 4.7e9, "funding_rate": 0.019, "oi": 78818},
            "ETH": {"price": 3340, "volume_24h": 1.5e9, "funding_rate": 0.015, "oi": 1552267},
        }

class MockLLMClient:
    """Mock LLM client for example"""
    def query(self, prompt: str):
        # In real bot, this would call DeepSeek API
        print("=" * 80)
        print("PROMPT SENT TO LLM:")
        print("=" * 80)
        print(prompt)
        print("=" * 80)
        return "DECISION: BUY SOL\nREASON: Strong funding rate, market in cautious optimism phase"


def format_market_data(market_data: dict) -> str:
    """Format market data table for LLM"""
    lines = ["Market Data (Latest):"]
    lines.append(f"{'Symbol':<8} {'Price':<12} {'24h Vol':<15} {'Funding':<10} {'OI':<15}")
    lines.append("-" * 70)

    for symbol, data in market_data.items():
        price = f"${data['price']:,.2f}"
        volume = f"${data['volume_24h']/1e9:.2f}B"
        funding = f"{data['funding_rate']:.4f}%"
        oi = f"{data['oi']:,.0f}"
        lines.append(f"{symbol:<8} {price:<12} {volume:<15} {funding:<10} {oi:<15}")

    return "\n".join(lines)


def main():
    """Main bot loop with macro context integration"""

    # Initialize macro context fetcher (refreshes every 12 hours)
    macro_fetcher = MacroContextFetcher(
        cambrian_api_key="doug.ZbEScx8M4zlf7kDn",
        refresh_interval_hours=12
    )

    # Initialize other components
    market_data_fetcher = MockMarketData()
    llm_client = MockLLMClient()

    print("🤖 LLM Trading Bot Started")
    print(f"⏰ Check interval: Every 5 minutes")
    print(f"🌍 Macro refresh: Every 12 hours")
    print()

    # Simulate multiple decision cycles
    for cycle in range(1, 4):
        print(f"\n{'=' * 80}")
        print(f"DECISION CYCLE #{cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 80}\n")

        # 1. Get macro context (cached if < 12 hours old)
        macro_context = macro_fetcher.get_macro_context()
        cache_age = macro_fetcher.get_cache_age()
        if cache_age:
            print(f"📊 Macro context age: {cache_age} (refreshes at 12 hours)\n")

        # 2. Fetch fresh market data (every cycle)
        market_data = market_data_fetcher.get_all_markets()
        market_table = format_market_data(market_data)

        # 3. Build prompt with BOTH macro context + market data
        prompt = f"""You are a trading agent. Analyze the market and make a decision.

{macro_context}

{market_table}

Open Positions: None

Instructions:
- Consider the macro context (overall market state, catalysts, outlook)
- Analyze current market data (price, volume, funding, OI)
- Make a decision: BUY <SYMBOL>, SELL <SYMBOL>, or NOTHING
- Explain your reasoning briefly (cite macro context + market data)

Respond in this exact format:
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | NOTHING]
REASON: [Your reasoning citing macro + market data]
"""

        # 4. Query LLM
        response = llm_client.query(prompt)

        # 5. Parse response (in real bot, this would execute trade)
        print("\nLLM Response:")
        print(response)
        print()

        # Simulate time between cycles
        if cycle < 3:
            print("⏳ Waiting 5 minutes until next check...")
            time.sleep(2)  # In real bot: time.sleep(300)


if __name__ == "__main__":
    main()
