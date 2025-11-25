"""
Position Sizing Configuration
Easy tuning of sizing parameters without touching code
"""

# ============================================================================
# SIZING MODE SELECTION
# ============================================================================

# Options: "conservative", "balanced", "aggressive", "adaptive"
SIZING_MODE = "adaptive"

# ============================================================================
# RESERVE & LIMITS
# ============================================================================

# Percentage of account to hold in reserve (safety buffer)
RESERVE_PERCENTAGE = 0.15  # 15% held back

# Maximum % of account for single position (risk cap)
MAX_SINGLE_POSITION_PCT = 0.20  # 20% max

# Maximum positions to hold simultaneously
MAX_POSITIONS = 15

# ============================================================================
# BASE CONFIDENCE MULTIPLIERS (by mode)
# ============================================================================

CONFIDENCE_MULTIPLIERS = {
    "conservative": {
        "<0.5":    0.6,
        "0.5-0.7": 0.8,
        "0.7-0.85": 1.0,
        "0.85+":   1.2
    },
    "balanced": {
        "<0.5":    0.7,
        "0.5-0.7": 1.0,
        "0.7-0.85": 1.3,
        "0.85+":   1.7
    },
    "aggressive": {
        "<0.5":    0.5,
        "0.5-0.7": 0.9,
        "0.7-0.85": 1.5,
        "0.85+":   2.2
    },
    "adaptive": {
        "<0.5":    0.7,
        "0.5-0.7": 1.0,
        "0.7-0.85": 1.4,
        "0.85+":   1.8
    }
}

# ============================================================================
# MOMENTUM ADJUSTMENT (MACD-based)
# ============================================================================

# Increase size on strong momentum (let runners run!)
MOMENTUM_ADJUSTMENTS = {
    "weak":        0.9,   # |MACD| < 0.1
    "moderate":    1.0,   # |MACD| 0.1-0.5
    "strong":      1.15,  # |MACD| 0.5-1.5
    "very_strong": 1.25   # |MACD| > 1.5
}

# MACD thresholds
MACD_THRESHOLDS = {
    "weak_max": 0.1,
    "moderate_max": 0.5,
    "strong_max": 1.5
}

# ============================================================================
# VOLATILITY ADJUSTMENT (ATR-based)
# ============================================================================

# Reduce size on high volatility (risk management)
VOLATILITY_ADJUSTMENTS = {
    "low":      1.2,   # ATR < 2% of price
    "normal":   1.0,   # ATR 2-4% of price
    "high":     0.85,  # ATR 4-7% of price
    "extreme":  0.7    # ATR > 7% of price
}

# ATR % thresholds
ATR_PCT_THRESHOLDS = {
    "low_max": 2.0,
    "normal_max": 4.0,
    "high_max": 7.0
}

# ============================================================================
# SETUP QUALITY ADJUSTMENT
# ============================================================================

# Reward high-quality setups with multiple indicators aligned
CONFLUENCE_BONUSES = {
    ">=75%_aligned": 1.2,   # 3+ of 4 indicators aligned
    ">=50%_aligned": 1.1,   # 2+ of 4 indicators aligned
    "default":       1.0
}

# Bonus for V2-style exact citations (quality reasoning)
V2_CITATION_BONUS = 1.05  # +5% for citing actual RSI/MACD values

# ============================================================================
# STREAK ADJUSTMENTS
# ============================================================================

# Adjust based on recent win/loss patterns
STREAK_ADJUSTMENTS = {
    "win_3+":    1.1,   # 3+ wins in a row
    "win_2":     1.05,  # 2 wins in a row
    "loss_3+":   0.85,  # 3+ losses in a row
    "loss_2":    0.92,  # 2 losses in a row
    "neutral":   1.0
}

# ============================================================================
# OVERALL CAPS
# ============================================================================

# Absolute multiplier limits (safety bounds)
MIN_TOTAL_MULTIPLIER = 0.5   # Never go below 50% of base
MAX_TOTAL_MULTIPLIER = 3.0   # Never go above 300% of base

# Exchange minimum (Lighter DEX requirement)
EXCHANGE_MINIMUM_USD = 10.0

# ============================================================================
# TRAILING STOPS & EXITS (Future enhancement)
# ============================================================================

# Enable trailing stops for runners
ENABLE_TRAILING_STOPS = False  # Set to True when ready

# Trailing stop settings
TRAILING_STOP_ACTIVATION = 1.5  # Start trailing at +1.5% profit
TRAILING_STOP_DISTANCE = 0.8    # Trail 0.8% below peak

# Partial profit taking
ENABLE_PARTIAL_EXITS = False  # Set to True when ready
PARTIAL_EXIT_LEVELS = [
    {"profit_pct": 2.0, "close_pct": 0.3},  # Close 30% at +2%
    {"profit_pct": 4.0, "close_pct": 0.5},  # Close 50% more at +4%
]

# ============================================================================
# QUICK PRESETS
# ============================================================================

PRESETS = {
    "volume_focused": {
        # Maximize volume with larger sizes
        "mode": "aggressive",
        "reserve_pct": 0.10,  # Lower reserve = more capital deployed
        "max_positions": 12,   # Fewer positions = larger each
        "description": "Larger positions for max volume"
    },
    "risk_managed": {
        # Conservative sizing, higher reserve
        "mode": "conservative",
        "reserve_pct": 0.20,  # Higher reserve
        "max_positions": 20,   # More diversification
        "description": "Smaller, safer positions"
    },
    "balanced_scalping": {
        # Default balanced approach
        "mode": "adaptive",
        "reserve_pct": 0.15,
        "max_positions": 15,
        "description": "Balanced risk/reward for scalping"
    }
}

# Active preset (or None to use individual settings above)
ACTIVE_PRESET = "balanced_scalping"

# ============================================================================
# HELPER: Get active config
# ============================================================================

def get_active_config():
    """Get the currently active sizing configuration"""
    if ACTIVE_PRESET and ACTIVE_PRESET in PRESETS:
        preset = PRESETS[ACTIVE_PRESET]
        return {
            "mode": preset["mode"],
            "reserve_pct": preset["reserve_pct"],
            "max_positions": preset["max_positions"],
            "min_usd": EXCHANGE_MINIMUM_USD,
            "description": preset["description"]
        }
    else:
        return {
            "mode": SIZING_MODE,
            "reserve_pct": RESERVE_PERCENTAGE,
            "max_positions": MAX_POSITIONS,
            "min_usd": EXCHANGE_MINIMUM_USD,
            "description": "Custom configuration"
        }
