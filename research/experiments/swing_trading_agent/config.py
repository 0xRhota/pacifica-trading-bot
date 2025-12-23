"""
Swing Trading Agent Configuration
Based on research from 2025-11-27-copy-trading-pivot

KEY FINDINGS FROM WINNING WALLET ANALYSIS:
- 75.5% win rate, $668k profit
- 90.2% of trades held 4+ hours
- Average hold time: 93.5 hours (3.9 days)
- NO scalping - swing trading only

KEY INSIGHT FROM QWEN ANALYSIS:
- Scalping requires 68% win rate with 2:1 negative R/R
- Swing trading only needs 25% win rate with 3:1 positive R/R
"""

# ============================================================================
# STRATEGY: SWING TRADING (v5)
# ============================================================================
STRATEGY_VERSION = "v5_swing_trading"
STRATEGY_FILE = "llm_agent/prompts_archive/v5_swing_trading.txt"

# ============================================================================
# RISK MANAGEMENT - 3:1 REWARD/RISK (from Qwen analysis)
# ============================================================================
# With 15% TP and 5% SL, we only need 25% win rate to break even
# This is MUCH more achievable than 68% required for scalping

TAKE_PROFIT_PCT = 15.0  # 15% take profit target
STOP_LOSS_PCT = 5.0     # 5% stop loss (wider than scalping)

# Required win rate with this R/R: 25%
# Expected win rate from research: 60%+ (with trend confirmation)

# ============================================================================
# HOLD TIME RULES (from winning wallet analysis)
# ============================================================================
# 90.2% of winning trades held 4+ hours
# Average hold: 93.5 hours (3.9 days)

MIN_HOLD_HOURS = 4.0        # Minimum 4 hours before considering exit
MAX_HOLD_HOURS = 96.0       # Maximum 4 days (opportunity cost)
IDEAL_HOLD_HOURS = 24.0     # Sweet spot for swing trades

# ============================================================================
# POSITION SIZING (from Qwen analysis)
# ============================================================================
# With small capital, use micro positions
# "1-5% of capital per trade"

POSITION_SIZE_PCT = 0.05    # 5% of capital per trade
MAX_POSITIONS = 3           # Only 2-3 positions at a time (quality over quantity)
MIN_POSITION_USD = 5.0      # Minimum $5 per position

# ============================================================================
# TRADING INTERVAL
# ============================================================================
# Swing trading doesn't need frequent checks
# Check every 30 minutes to 1 hour

CHECK_INTERVAL_SECONDS = 1800  # 30 minutes between cycles

# ============================================================================
# ENTRY CRITERIA (from research)
# ============================================================================
# Only enter when ALL criteria are met

LONG_CRITERIA = {
    "trend": "SMA20 > SMA50",       # Uptrend required
    "rsi_min": 30,                   # Oversold
    "rsi_max": 45,                   # But not dead
    "macd": "positive OR bullish crossover",
    "volume": "> 1x average"
}

SHORT_CRITERIA = {
    "trend": "SMA20 < SMA50",       # Downtrend required
    "rsi_min": 55,                   # Overbought
    "rsi_max": 70,                   # But still has room
    "macd": "negative OR bearish crossover",
    "volume": "> 1x average"
}

# ============================================================================
# ASSETS TO TRADE
# ============================================================================
# High liquidity only - avoid illiquid assets

HIBACHI_ASSETS = [
    "SOL/USDT-P",
    "ETH/USDT-P",
    "BTC/USDT-P",
]

EXTENDED_ASSETS = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
]

# ============================================================================
# BLACKLISTED ASSETS (historically losing)
# ============================================================================
BLACKLIST = [
    "SEI",   # High loss rate from previous analysis
    "ZEC",   # High loss rate from previous analysis
    "SUI",   # 0% win rate from previous analysis
]

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FILE = "logs/swing_trading_bot.log"
