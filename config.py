"""
Configuration settings for Pacifica Trading Bot
"""

import os
from typing import List

class BotConfig:
    # API Configuration
    API_KEY = "7a7voQH3WWD1fi6B25gWSzCUicvmrbtJh8sb2McJeWeg"
    BASE_URL = "https://api.pacifica.fi/api/v1"
    ACCOUNT_ADDRESS = "8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc"
    
    # Trading Parameters
    MIN_POSITION_SIZE_USD = 10.0   # Minimum position size (Pacifica requirement)
    MAX_POSITION_SIZE_USD = 15.0   # Maximum position size in USD (small to start)
    MIN_PROFIT_THRESHOLD = 0.002   # 0.2% minimum profit to close
    MAX_LOSS_THRESHOLD = 0.003     # 0.3% maximum loss before closing
    MAX_LEVERAGE = 5.0             # Maximum leverage to use
    LOT_SIZE = 0.01                # Minimum increment for order size

    # Timing Configuration
    CHECK_FREQUENCY_SECONDS = 45   # How often to check positions
    TRADE_FREQUENCY_SECONDS = 900  # How often to open new positions (15 minutes)
    MAX_POSITION_HOLD_TIME = 1800  # Max time to hold position (30 minutes)
    
    # Symbols to trade (Pacifica uses simple symbols: BTC, SOL, ETH)
    TRADING_SYMBOLS = [
        "SOL",
        "BTC",
        "ETH"
    ]
    
    # Trading Strategy
    VOLUME_TARGET_DAILY = 1000.0   # Target daily volume in USD (reduced for small account)
    SMALL_TRADE_SIZE = 8.0         # Small trade size for volume farming ($5-10)
    LONGS_ONLY = True              # Bull market mode - only long positions
    DRY_RUN = True                 # Dry run mode - simulate trades without placing orders
    
    # Risk Management
    MAX_DAILY_LOSS = 200.0         # Maximum daily loss in USD
    STOP_TRADING_ON_LOSS = True    # Stop trading if daily loss limit hit
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_TO_FILE = True
    LOG_FILE = "trading_bot.log"