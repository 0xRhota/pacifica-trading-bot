"""
High Volume Trading Agent Configuration
Based on Qwen analysis 2025-11-27

KEY INSIGHT: 50+ trades/day = guaranteed loss due to fees
SOLUTION: 10-20 trades/day with 4:1 R/R = +3% daily profit at 25% win rate
"""

# ============================================================================
# STRATEGY VERSION
# ============================================================================
STRATEGY_VERSION = "v6_high_volume"
STRATEGY_FILE = "llm_agent/prompts_archive/v6_high_volume.txt"

# ============================================================================
# RISK MANAGEMENT - 4:1 R/R (from Qwen analysis)
# ============================================================================
# Required win rate: 22%
# Expected win rate: 25%+
# Expected daily profit: +3%

TAKE_PROFIT_PCT = 4.0   # 4% take profit
STOP_LOSS_PCT = 1.0     # 1% stop loss (tight, cut fast)

# ============================================================================
# TIME-BASED EXIT - THE KEY TO HIGH VOLUME
# ============================================================================
# Close positions after 1 hour regardless of P/L
# This prevents holding through reversals and maintains volume

TIME_EXIT_MINUTES = 60  # 1 hour max hold
MIN_HOLD_MINUTES = 5    # Minimum 5 minutes (avoid instant exits)

# ============================================================================
# TRADE FREQUENCY
# ============================================================================
# Target: 10-20 trades per day
# Check interval: 10 minutes (6 checks per hour, 144 per day)
# Max trades: 20 per day (caps fees at ~3%)

CHECK_INTERVAL_SECONDS = 600  # 10 minutes between checks
MAX_TRADES_PER_DAY = 20       # Stop trading after 20 trades
MAX_DAILY_LOSS_PCT = 2.0      # Stop trading if down 2%

# ============================================================================
# POSITION SIZING
# ============================================================================
POSITION_SIZE_PCT = 0.01  # 1% of capital per trade
MAX_POSITIONS = 3         # Up to 3 concurrent positions
MIN_POSITION_USD = 5.0    # Minimum $5 per position

# ============================================================================
# ENTRY CRITERIA (ALL must be true)
# ============================================================================
# These are reference values - actual checks in the bot
ENTRY_CRITERIA = {
    "long": {
        "trend": "price > SMA50",
        "rsi_max": 30,           # RSI must be below 30
        "rsi_direction": "rising",
        "volume_multiplier": 1.0  # Volume > average
    },
    "short": {
        "trend": "price < SMA50",
        "rsi_min": 70,           # RSI must be above 70
        "rsi_direction": "falling",
        "volume_multiplier": 1.0  # Volume > average
    }
}

# ============================================================================
# ASSETS
# ============================================================================
TRADEABLE_ASSETS = ["BTC", "ETH", "SOL"]

# Hibachi format
HIBACHI_SYMBOLS = [
    "BTC/USDT-P",
    "ETH/USDT-P",
    "SOL/USDT-P"
]

# Extended format
EXTENDED_SYMBOLS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD"
]

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FILE = "logs/high_volume_bot.log"

# ============================================================================
# LLM SETTINGS
# ============================================================================
# LLM is used for entry decisions, not exits
# Exits are handled by hard rules (TP/SL/Time)
LLM_TEMPERATURE = 0.1  # Low temperature for consistent decisions
LLM_MAX_TOKENS = 500
