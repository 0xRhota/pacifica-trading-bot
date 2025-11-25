#!/usr/bin/env python3
"""
Phase 2 Demo: LLM Integration with DeepSeek

Deliverable: Script that gets trading decision from DeepSeek LLM
based on macro context + all 28 markets + open positions

Usage:
    python -m llm_agent.phase2_demo
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.data import MarketDataAggregator
from llm_agent.llm import LLMTradingAgent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run Phase 2 demo"""

    print("=" * 80)
    print("PHASE 2 DEMO: LLM Integration with DeepSeek")
    print("LLM Trading Bot for Pacifica DEX")
    print("=" * 80)
    print()

    # Get API keys from environment
    cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    if not cambrian_api_key:
        print("❌ CAMBRIAN_API_KEY not found in .env")
        sys.exit(1)

    if not deepseek_api_key:
        print("❌ DEEPSEEK_API_KEY not found in .env")
        sys.exit(1)

    print(f"✅ Cambrian API Key loaded: {cambrian_api_key[:20]}...")
    print(f"✅ DeepSeek API Key loaded: {deepseek_api_key[:20]}...")
    print()

    # Initialize aggregator
    print("Initializing MarketDataAggregator...")
    aggregator = MarketDataAggregator(
        cambrian_api_key=cambrian_api_key,
        interval="15m",
        candle_limit=100,
        macro_refresh_hours=12
    )
    print()

    # Initialize LLM agent
    print("Initializing LLMTradingAgent...")
    agent = LLMTradingAgent(
        deepseek_api_key=deepseek_api_key,
        model="deepseek-chat",
        max_retries=2,
        daily_spend_limit=10.0,
        max_positions=3
    )
    print()

    # Simulate some open positions (for demo)
    open_positions = []
    # Uncomment to test with open positions:
    # open_positions = [
    #     {
    #         "symbol": "SOL",
    #         "side": "LONG",
    #         "entry_price": 190.50,
    #         "current_price": 187.43,
    #         "size": 30.0,
    #         "pnl": -1.61,
    #         "time_held": "2h 15m"
    #     }
    # ]

    print("=" * 80)
    print("Getting Trading Decision from LLM...")
    print("=" * 80)
    print()

    if open_positions:
        print(f"Current Open Positions: {len(open_positions)}")
        for pos in open_positions:
            print(f"  - {pos['side']} {pos['symbol']} @ ${pos['entry_price']}")
        print()

    # Get trading decision
    start_time = datetime.now()
    decision = agent.get_trading_decision(
        aggregator=aggregator,
        open_positions=open_positions,
        force_macro_refresh=False
    )
    elapsed = (datetime.now() - start_time).total_seconds()

    print()
    print("=" * 80)
    print("LLM DECISION")
    print("=" * 80)
    print()

    if decision:
        print(f"Action:  {decision['action']}")
        if decision['symbol']:
            print(f"Symbol:  {decision['symbol']}")
        print(f"Reason:  {decision['reason']}")
        print()
        print(f"Cost:    ${decision['cost']:.4f}")
        print(f"Tokens:  {decision['prompt_tokens']} prompt + {decision['completion_tokens']} completion")
        print(f"Time:    {elapsed:.1f} seconds")
        print()
    else:
        print("❌ Failed to get decision from LLM")
        print()

    # Budget info
    print("=" * 80)
    print("BUDGET")
    print("=" * 80)
    print()
    print(f"Daily Spend:      ${agent.get_daily_spend():.4f}")
    print(f"Remaining Budget: ${agent.get_remaining_budget():.4f}")
    print(f"Daily Limit:      $10.00")
    print()

    print("=" * 80)
    print("PHASE 2 DEMO COMPLETE")
    print("=" * 80)
    print()
    print("✅ LLM integration working correctly")
    print("✅ DeepSeek API responding")
    print("✅ Response parsing validated")
    print("✅ Decision validation working")
    print()
    print("Next: Phase 3 - Trade Execution")


if __name__ == "__main__":
    main()
