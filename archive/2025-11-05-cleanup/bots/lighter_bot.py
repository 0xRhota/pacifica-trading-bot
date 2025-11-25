#!/usr/bin/env python3
"""Lighter Bot - Thin wrapper using unified core"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trading_bot import UnifiedTradingBot
from core.executor import UnifiedExecutor
from core.logger import UnifiedLogger
from dexes.lighter.adapter import LighterAdapter
from strategies.llm_strategy import LLMStrategy

# Load environment variables
load_dotenv()


async def main():
    """Main bot entry point"""
    # Initialize adapter
    # Support both old and new env var names for compatibility
    api_key_private = os.getenv("LIGHTER_PRIVATE_KEY") or os.getenv("LIGHTER_API_KEY_PRIVATE")
    api_key_public = os.getenv("LIGHTER_PUBLIC_KEY") or os.getenv("LIGHTER_API_KEY_PUBLIC")
    
    adapter = LighterAdapter(
        api_key_private=api_key_private,
        api_key_public=api_key_public,
        account_index=int(os.getenv("LIGHTER_ACCOUNT_INDEX", "341823")),
        api_key_index=int(os.getenv("LIGHTER_API_KEY_INDEX", "2"))
    )
    
    # Initialize logger (needed for strategy)
    logger = UnifiedLogger("lighter")
    
    # Initialize LLM strategy (DeepSeek-based decisions with all indicators)
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_KEY")
    cambrian_api_key = os.getenv("CAMBRIAN_API_KEY")
    
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY or DEEPSEEK_KEY is required. Check your .env file.")
    
    strategy = LLMStrategy(
        deepseek_api_key=deepseek_api_key,
        cambrian_api_key=cambrian_api_key or "",
        max_positions=15,
        logger_instance=logger  # Pass logger to strategy for detailed LLM logging
    )
    
    # Initialize executor
    executor = UnifiedExecutor(
        adapter=adapter,
        logger_instance=logger,
        dry_run=False,  # Set to True for testing
        default_position_size=12.0,  # $12 to meet $10 minimum (even at 0.8x confidence = $9.60)
        max_positions=15
    )
    
    # Create bot
    # Focus on high-volume tokens only for now
    allowed_tokens = ['BTC', 'ETH', 'ZEC', 'PENGU', 'SOL']
    
    config = {
        'bot_name': 'lighter',
        'dry_run': False,
        'interval': 300,  # 5 minutes - LLM analyzes all indicators every cycle
        'max_positions': 15,
        'executor': executor,
        'data_fetcher': None,  # Adapter handles data fetching
        'allowed_tokens': allowed_tokens,  # Whitelist of tokens to trade
    }
    
    bot = UnifiedTradingBot(adapter, strategy, config)
    
    # Initialize and validate
    await bot.initialize()
    
    # Run
    logger.info("Starting Lighter bot...", component="lighter_bot")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())

