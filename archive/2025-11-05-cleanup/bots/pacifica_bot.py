#!/usr/bin/env python3
"""Pacifica Bot - Thin wrapper using unified core"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trading_bot import UnifiedTradingBot
from core.executor import UnifiedExecutor
from core.logger import UnifiedLogger
from dexes.pacifica.adapter import PacificaAdapter
from strategies.high_volume_scalping_strategy import HighVolumeScalpingStrategy

# Load environment variables
load_dotenv()


async def main():
    """Main bot entry point"""
    # Initialize adapter
    adapter = PacificaAdapter(
        private_key=os.getenv("PACIFICA_API_KEY"),
        account_address=os.getenv("PACIFICA_ACCOUNT")
    )
    
    # Initialize strategy (high volume scalping - same as Lighter)
    strategy = HighVolumeScalpingStrategy(
        profit_target=0.015,  # 1.5% profit target
        stop_loss=0.003,      # 0.3% stop loss
        max_positions=15
    )
    
    # Initialize executor
    logger = UnifiedLogger("pacifica")
    executor = UnifiedExecutor(
        adapter=adapter,
        logger_instance=logger,
        dry_run=False,  # Set to True for testing
        default_position_size=30.0,
        max_positions=15
    )
    
    # Create bot
    config = {
        'bot_name': 'pacifica',
        'dry_run': False,
        'interval': 300,  # 5 minutes (can be adjusted for higher frequency)
        'max_positions': 15,
        'executor': executor,
        'data_fetcher': None,  # Adapter handles data fetching
    }
    
    bot = UnifiedTradingBot(adapter, strategy, config)
    
    # Initialize and validate
    await bot.initialize()
    
    # Run
    logger.info("Starting Pacifica bot...", component="pacifica_bot")
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())

