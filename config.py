"""
Unified Configuration for All Trading Bots
Single source of truth - no hardcoded values in bot files
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

class PacificaConfig:
    """Pacifica DEX (Solana) configuration"""

    # API
    API_KEY = "7a7voQH3WWD1fi6B25gWSzCUicvmrbtJh8sb2McJeWeg"
    BASE_URL = "https://api.pacifica.fi/api/v1"
    ACCOUNT_ADDRESS = "8saejVsbEBraGvxbJGxrosv4QKMfR2i8f59GFAnMXfMc"

    # Fees
    TAKER_FEE = 0.0004  # 0.04%

    # Position Sizing
    MIN_POSITION_USD = 30.0
    MAX_POSITION_USD = 40.0

    # Symbol-specific lot sizes (DEX enforced)
    LOT_SIZES = {
        "SOL": 0.01,      # 0.01 SOL min
        "ETH": 0.01,      # 0.01 ETH min
        "BTC": 0.001,     # 0.001 BTC min (~$122)
        "PENGU": 1,       # 1 PENGU min
        "XPL": 1,         # 1 XPL min
        "ASTER": 1,       # 1 ASTER min
    }

    # Symbols to trade (BTC excluded - min lot > max position)
    TRADING_SYMBOLS = ["SOL", "PENGU"]

    # Risk Management
    TAKE_PROFIT_LEVELS = [0.02, 0.04, 0.06]  # 2%, 4%, 6%
    TAKE_PROFIT_SIZES = [0.33, 0.33, 0.34]   # Exit 1/3 at each level
    STOP_LOSS = 0.01  # 1%
    MAX_LEVERAGE = 5.0

    # Orderbook Filters
    MAX_SPREAD_PCT = 0.1    # Skip if > 0.1%
    MIN_ORDER_COUNT = 5     # Skip if < 5 orders per side
    WEIGHTED_DEPTH = True   # Weight by distance from mid

    # Timing
    CHECK_FREQUENCY_SEC = 45     # Check positions every 45s
    TRADE_FREQUENCY_SEC = 900    # Open new positions every 15min
    MAX_HOLD_TIME_SEC = None     # No time limit

    # Strategy
    IMBALANCE_LONG_THRESHOLD = 1.3   # Bid/Ask > 1.3 = long
    IMBALANCE_SHORT_THRESHOLD = 0.7  # Bid/Ask < 0.7 = short


class LighterConfig:
    """Lighter DEX (zkSync) configuration"""

    # API (from env)
    API_KEY_PUBLIC = os.getenv("LIGHTER_API_KEY_PUBLIC")
    API_KEY_PRIVATE = os.getenv("LIGHTER_API_KEY_PRIVATE")
    BASE_URL = "https://mainnet.zklighter.elliot.ai"
    ACCOUNT_INDEX = 126039
    API_KEY_INDEX = int(os.getenv("LIGHTER_API_KEY_INDEX", "3"))

    # Fees
    TAKER_FEE = 0.0  # Zero fees!

    # Position Sizing
    POSITION_USD = 20.0  # Fixed $20 per trade

    # Symbol-specific lot sizes
    LOT_SIZES = {
        "SOL": 0.01,
        "BTC": 0.01,
        "ETH": 0.01,
        "PENGU": 1,
        "XPL": 1,
        "ASTER": 1,
    }

    # Symbols to trade
    TRADING_SYMBOLS = ["SOL", "ETH", "BTC", "PENGU", "XPL", "ASTER"]

    # Risk Management
    TAKE_PROFIT = 0.03  # 3%
    STOP_LOSS = 0.01    # 1% (3:1 R:R)

    # VWAP Strategy
    VWAP_DEVIATION_THRESHOLD = 0.003  # 0.3% from VWAP
    VWAP_CANDLES = 9                   # 9 x 15min = 2.25 hours
    VWAP_INTERVAL = "15m"
    IMBALANCE_THRESHOLD = 1.3          # Orderbook confirmation

    # Timing
    CHECK_FREQUENCY_SEC = 300  # Check every 5min


class GlobalConfig:
    """Global settings across all bots"""

    # Solana
    SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY")

    # Logging
    LOG_DIR = "logs"
    LOG_LEVEL = "INFO"

    # Monitoring
    HEALTH_CHECK_INTERVAL_SEC = 300  # 5min

    # Risk Limits (global circuit breakers)
    MAX_DAILY_LOSS_USD = 50.0
    MAX_OPEN_POSITIONS = 3
    EMERGENCY_STOP_FILE = ".emergency_stop"  # Touch this file to halt all bots


# Validation on import
def validate_config():
    """Validate configuration on import"""
    errors = []

    # Check required env vars
    if not GlobalConfig.SOLANA_PRIVATE_KEY:
        errors.append("SOLANA_PRIVATE_KEY not set in environment")
    if not LighterConfig.API_KEY_PUBLIC:
        errors.append("LIGHTER_API_KEY_PUBLIC not set in environment")
    if not LighterConfig.API_KEY_PRIVATE:
        errors.append("LIGHTER_API_KEY_PRIVATE not set in environment")

    # Check lot sizes match trading symbols
    for symbol in PacificaConfig.TRADING_SYMBOLS:
        if symbol not in PacificaConfig.LOT_SIZES:
            errors.append(f"Pacifica: {symbol} missing from LOT_SIZES")

    for symbol in LighterConfig.TRADING_SYMBOLS:
        if symbol not in LighterConfig.LOT_SIZES:
            errors.append(f"Lighter: {symbol} missing from LOT_SIZES")

    # Check log directory exists
    import os
    if not os.path.exists(GlobalConfig.LOG_DIR):
        os.makedirs(GlobalConfig.LOG_DIR)

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

validate_config()

# Backwards compatibility
BotConfig = PacificaConfig  # Old code uses BotConfig
