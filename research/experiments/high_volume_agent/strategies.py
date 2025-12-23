"""
High Volume Strategy Variations
Two strategies for A/B testing:

STRATEGY A (Hibachi): Time-Capped
- 4% TP, 1% SL (4:1 R/R)
- MAX 1 HOUR hold (force close)
- Rationale: High turnover, consistent volume

STRATEGY B (Extended): Let Runners Run
- 4% TP, 1% SL (4:1 R/R)
- NO time limit (can hold for days)
- Trailing stop activates at +2%
- Rationale: Winners can run, losers cut quick

Both aim for 10-20 trades/day but with different exit philosophies.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class StrategyConfig:
    """Strategy configuration for A/B testing"""
    name: str
    take_profit_pct: float
    stop_loss_pct: float
    max_hold_hours: Optional[float]  # None = no limit
    min_hold_minutes: float
    trailing_stop_enabled: bool
    trailing_stop_activation_pct: float  # Activate trailing at +X%
    trailing_stop_distance_pct: float    # Trail by X% from peak
    check_interval_seconds: int
    max_trades_per_day: int


# ============================================================================
# STRATEGY A: TIME-CAPPED (for Hibachi)
# ============================================================================
STRATEGY_A_TIME_CAPPED = StrategyConfig(
    name="TIME_CAPPED",
    take_profit_pct=4.0,      # Exit at +4%
    stop_loss_pct=1.0,        # Exit at -1%
    max_hold_hours=1.0,       # FORCE CLOSE after 1 hour
    min_hold_minutes=5.0,     # Min 5 min to avoid immediate exits
    trailing_stop_enabled=False,
    trailing_stop_activation_pct=0.0,
    trailing_stop_distance_pct=0.0,
    check_interval_seconds=600,  # 10 minutes
    max_trades_per_day=20,
)


# ============================================================================
# STRATEGY B: LET RUNNERS RUN (for Extended)
# ============================================================================
STRATEGY_B_RUNNERS_RUN = StrategyConfig(
    name="RUNNERS_RUN",
    take_profit_pct=8.0,      # Higher TP - let winners run
    stop_loss_pct=1.0,        # Same tight SL - cut losers quick
    max_hold_hours=None,      # NO TIME LIMIT - runners can run
    min_hold_minutes=5.0,     # Min 5 min
    trailing_stop_enabled=True,   # Trailing stop for winners
    trailing_stop_activation_pct=2.0,  # Activate trail at +2%
    trailing_stop_distance_pct=1.5,    # Trail 1.5% from peak
    check_interval_seconds=600,  # 10 minutes
    max_trades_per_day=20,
)


# ============================================================================
# STRATEGY COMPARISON
# ============================================================================
"""
┌─────────────────────────────────────────────────────────────────────────┐
│                    A/B TEST COMPARISON                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STRATEGY A: TIME_CAPPED (Hibachi)                                     │
│  ─────────────────────────────────                                     │
│  • TP: 4%  SL: 1%  R/R: 4:1                                           │
│  • Max Hold: 1 HOUR (force close)                                      │
│  • Trailing Stop: OFF                                                  │
│  • Philosophy: High turnover, many small wins                          │
│  • Risk: Missing big moves, over-trading                               │
│                                                                         │
│  STRATEGY B: RUNNERS_RUN (Extended)                                    │
│  ────────────────────────────────────                                  │
│  • TP: 8%  SL: 1%  R/R: 8:1                                           │
│  • Max Hold: UNLIMITED                                                 │
│  • Trailing Stop: ON (activates at +2%, trails by 1.5%)               │
│  • Philosophy: Cut losers quick, let winners run                       │
│  • Risk: Lower trade volume, bigger drawdowns if wrong                 │
│                                                                         │
│  EXPECTED RESULTS (at 25% win rate):                                   │
│  ─────────────────────────────────────                                 │
│  Strategy A: 20 trades × (5×3.9% - 15×1.1%) = +3%/day                 │
│  Strategy B: 10 trades × (2.5×7.9% - 7.5×1.1%) = +11.5%/day           │
│              BUT trades may be slower to close                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
"""


def get_strategy_for_dex(dex: str) -> StrategyConfig:
    """Get strategy config based on DEX"""
    if dex.lower() == "hibachi":
        return STRATEGY_A_TIME_CAPPED
    elif dex.lower() == "extended":
        return STRATEGY_B_RUNNERS_RUN
    else:
        raise ValueError(f"Unknown DEX: {dex}")


def print_strategy_comparison():
    """Print strategy comparison for logging"""
    print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                    A/B TEST: TWO STRATEGIES                            ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  HIBACHI (Strategy A: TIME_CAPPED)                                    ║
║  • 4% TP, 1% SL, 1 HOUR MAX                                           ║
║  • High turnover, many trades                                          ║
║                                                                        ║
║  EXTENDED (Strategy B: RUNNERS_RUN)                                   ║
║  • 8% TP, 1% SL, NO TIME LIMIT                                        ║
║  • Trailing stop at +2%, let winners run                               ║
║                                                                        ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
