"""
Test DeepSeek API with Full LLM Trading Bot Prompt
Priority 1 prerequisite before Phase 1 development

Tests:
1. API authentication
2. Full 3-section prompt (macro + market data + positions)
3. Response format validation
4. Token count measurement
"""

import os
import requests
import json
from datetime import datetime

# Load API key from .env
from dotenv import load_dotenv
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def create_sample_prompt():
    """Create full 3-section prompt matching PRD spec"""

    # Section 1: Macro Context (from Deep42)
    macro_context = """======================================================================
MACRO CONTEXT (Market State)
Last Updated: 2025-10-30 00:49 UTC
======================================================================

Market Analysis:
The cryptocurrency market is currently showing **bullish reversal signs** and a highly **positive sentiment**.

### 1. Overall Market Sentiment
Sentiment is strong, driven by macroeconomic expectations. The weakening of Bitcoin dominance is a key technical signal, suggesting capital rotation and the potential for an imminent **Altseason** breakout.

### 2. Upcoming Catalysts/Events
The most significant near-term event is the expected **FOMC interest rate decision** this week. An anticipated interest rate cut is acting as a major bullish catalyst across the entire market, reducing the cost of capital and potentially boosting risk assets like crypto.

### 3. Short-Term and Mid-Term Outlook

| Asset Class | Short-Term Outlook | Mid-Term Outlook | Key Drivers |
| :--- | :--- | :--- | :--- |
| **Bitcoin (BTC)** | Favorable, expected to consolidate or push higher post-FOMC. | Bullish, with institutional flow via spot ETFs providing a stable base. | Macro-liquidity conditions (Fed policy) and ETF inflows. |
| **Major Altcoins**| Very Favorable, due to weakening BTC dominance and capital rotation. | Highly Bullish, anticipating an official "Altseason." | Specific token upgrades (e.g., Ethereum), L2 growth, and bullish momentum. |

The market is poised for a surge, with high-potential altcoins (including but not limited to ETH and SOL) expected to deliver massive upside as Bitcoin's dominance gives way.

Quick Metrics:
  Market Cap 24h: -1.03% 📉
  BTC Dominance: 57.53% (Moderate)
  Fear & Greed: 34/100 (Fear) 😰

======================================================================
"""

    # Section 2: Market Data (sample for 5 markets)
    market_data = """
Market Data (Latest):
Symbol   Price        24h Vol         Funding    OI              RSI    MACD      SMA20>50
-----------------------------------------------------------------------------------------------
SOL      $195.40      $2.30B          0.0125%    8,055,793       52     +0.8      Yes
BTC      $110,885.00  $4.70B          0.0190%    78,818          48     -0.3      No
ETH      $3,340.00    $1.50B          0.0150%    1,552,267       55     +1.2      Yes
PUMP     $0.45        $890M           0.0100%    35,443,580,570  72     +2.5      Yes
XRP      $2.10        $1.80B          0.0080%    201,911,884     44     -0.5      No
"""

    # Section 3: Open Positions
    positions = """
Open Positions: None
"""

    # Instructions
    instructions = """
Instructions:
- Consider the macro context (overall market state, catalysts, outlook)
- Analyze current market data (price, volume, funding, OI, indicators)
- Make a decision: BUY <SYMBOL>, SELL <SYMBOL>, or NOTHING
- Explain your reasoning briefly (cite macro context + market data)

Respond in this exact format:
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | NOTHING]
REASON: [Your reasoning citing macro + market data in 2-3 sentences]
"""

    full_prompt = f"""You are a trading agent. Analyze the market and make a decision.

{macro_context}

{market_data}

{positions}

{instructions}
"""

    return full_prompt


def test_deepseek_api():
    """Test DeepSeek API with full prompt"""

    print("=" * 80)
    print("DEEPSEEK API TEST - Full LLM Trading Bot Prompt")
    print("=" * 80)
    print()

    # Check API key
    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY not found in .env")
        print("Please add your DeepSeek API key to .env file")
        return

    print(f"✅ API Key found: {DEEPSEEK_API_KEY[:20]}...")
    print()

    # Create prompt
    print("📝 Creating full 3-section prompt...")
    prompt = create_sample_prompt()

    # Estimate token count (rough: 4 chars = 1 token)
    estimated_tokens = len(prompt) // 4
    print(f"📊 Prompt length: {len(prompt)} characters")
    print(f"📊 Estimated tokens: ~{estimated_tokens} (actual may vary)")
    print()

    # Show prompt preview
    print("📄 Prompt Preview (first 500 chars):")
    print("-" * 80)
    print(prompt[:500] + "...")
    print("-" * 80)
    print()

    # API request
    print("🚀 Sending request to DeepSeek API...")
    print(f"   URL: {DEEPSEEK_URL}")
    print(f"   Model: deepseek-chat")
    print(f"   Max tokens: 50")
    print(f"   Temperature: 0.1")
    print()

    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }

        response = requests.post(
            DEEPSEEK_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        # Check response
        if response.status_code == 200:
            data = response.json()

            print("✅ API call successful!")
            print()
            print("=" * 80)
            print("RESPONSE DATA:")
            print("=" * 80)
            print(json.dumps(data, indent=2))
            print()

            # Extract response
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]

                print("=" * 80)
                print("LLM RESPONSE:")
                print("=" * 80)
                print(content)
                print()

                # Validate format
                print("=" * 80)
                print("FORMAT VALIDATION:")
                print("=" * 80)

                lines = content.strip().split("\n")
                decision_line = lines[0] if lines else ""

                if decision_line.startswith("DECISION:"):
                    print("✅ Response starts with 'DECISION:'")

                    # Extract decision
                    decision_part = decision_line.replace("DECISION:", "").strip()

                    if "BUY" in decision_part or "SELL" in decision_part or "NOTHING" in decision_part:
                        print(f"✅ Valid decision found: {decision_part}")
                    else:
                        print(f"⚠️ Unexpected decision format: {decision_part}")

                    # Check for REASON
                    if len(lines) > 1 and "REASON:" in content:
                        print("✅ Response includes 'REASON:'")
                    else:
                        print("⚠️ Response missing 'REASON:' section")
                else:
                    print(f"❌ Response does NOT start with 'DECISION:': {decision_line}")

                print()

                # Token usage
                if "usage" in data:
                    usage = data["usage"]
                    print("=" * 80)
                    print("TOKEN USAGE:")
                    print("=" * 80)
                    print(f"  Prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                    print(f"  Completion tokens: {usage.get('completion_tokens', 'N/A')}")
                    print(f"  Total tokens: {usage.get('total_tokens', 'N/A')}")
                    print()
                    print(f"  Estimated tokens: {estimated_tokens}")
                    print(f"  Actual prompt tokens: {usage.get('prompt_tokens', 'N/A')}")
                    print(f"  Accuracy: {estimated_tokens / usage.get('prompt_tokens', 1):.2%}")
            else:
                print("⚠️ No choices in response")

        elif response.status_code == 401:
            print("❌ Authentication failed (401 Unauthorized)")
            print("   Check your DEEPSEEK_API_KEY in .env")
            print()
            print("Response:", response.text)

        elif response.status_code == 429:
            print("❌ Rate limit exceeded (429 Too Many Requests)")
            print("   Wait a moment and try again")
            print()
            print("Response:", response.text)

        else:
            print(f"❌ API call failed: HTTP {response.status_code}")
            print()
            print("Response:", response.text)

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")

    except Exception as e:
        print(f"❌ Error: {e}")

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_deepseek_api()
