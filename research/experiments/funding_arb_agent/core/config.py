"""
Arbitrage Configuration
=======================
Timing, sizing, and strategy parameters for the funding rate arbitrage bot.

Key Design Decisions (from user requirements):
- Longer intervals (15-30 min) since funding settles every 8h
- High volume generation through position rotation
- Position rotation every 1-2 hours to churn volume
- Delta-neutral at all times
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ArbConfig:
    """Configuration for the funding rate arbitrage strategy"""

    # ===== TIMING =====

    # How often to check funding rates and rebalance (seconds)
    # 15-30 minutes is optimal since funding settles every 8h
    scan_interval: int = 900  # 15 minutes

    # How often to rotate positions for volume generation (seconds)
    # Rotate every 1-2 hours to generate significant volume
    rotation_interval: int = 3600  # 1 hour

    # Minimum time between trades on same symbol (seconds)
    # Prevents rapid-fire trading issues
    min_trade_interval: int = 60  # 1 minute

    # ===== POSITION SIZING =====

    # Position size per leg (USD)
    # Each exchange gets this amount, so total exposure is 2x but delta-neutral
    position_size_usd: float = 100.0  # $100 per exchange per symbol

    # Maximum total position size across all symbols (USD per exchange)
    max_total_position_usd: float = 500.0

    # Minimum spread to open new positions (annualized %)
    # Qwen recommended 10-15% after fees
    min_spread_threshold: float = 5.0  # 5% annualized

    # Spread below which to close positions (annualized %)
    # Close if arbitrage becomes unprofitable
    close_spread_threshold: float = 2.0  # 2% annualized

    # ===== VOLUME GENERATION =====

    # Enable position rotation for volume generation
    enable_rotation: bool = True

    # Rotation generates 2 trades per exchange per rotation (close + open)
    # With 1 hour rotation and $100 positions:
    # - 24 rotations/day * 2 trades * 2 exchanges * $100 = $9,600 daily volume per symbol
    # - 3 symbols = ~$28,800 daily volume

    # Random rotation offset (seconds) to avoid predictable patterns
    rotation_jitter: int = 300  # +/- 5 minutes

    # ===== SYMBOLS =====

    # Symbols to trade (normalized format)
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])

    # ===== RISK MANAGEMENT =====

    # Maximum allowed delta imbalance (USD)
    # If |long_notional - short_notional| > this, rebalance immediately
    max_delta_imbalance_usd: float = 50.0

    # Stop loss per position (% of position size)
    # If unrealized PnL drops below this, close both legs
    stop_loss_pct: float = 5.0

    # Maximum drawdown before halting (% of equity)
    max_drawdown_pct: float = 10.0

    # ===== EXECUTION =====

    # Dry run mode (no actual orders)
    dry_run: bool = True

    # Slippage tolerance (%)
    slippage_tolerance: float = 0.5

    # Order timeout (seconds)
    order_timeout: int = 30

    # ===== LOGGING =====

    # Log level
    log_level: str = "INFO"

    # Log file path
    log_file: str = "logs/funding_arb.log"

    def __post_init__(self):
        """Validate configuration"""
        assert self.scan_interval >= 60, "Scan interval must be at least 60 seconds"
        assert self.rotation_interval >= 300, "Rotation interval must be at least 5 minutes"
        assert self.position_size_usd > 0, "Position size must be positive"
        assert self.min_spread_threshold > self.close_spread_threshold, \
            "Min spread must be greater than close spread"

    @classmethod
    def high_volume(cls) -> 'ArbConfig':
        """
        High volume preset - maximizes trading volume.

        - Rotates every 30 minutes
        - Larger position sizes
        - Lower spread threshold to capture more opportunities
        """
        return cls(
            scan_interval=600,  # 10 minutes
            rotation_interval=1800,  # 30 minutes
            position_size_usd=200.0,  # $200 per leg
            max_total_position_usd=1000.0,
            min_spread_threshold=3.0,  # More aggressive
            close_spread_threshold=1.0,
            enable_rotation=True,
            rotation_jitter=180,
        )

    @classmethod
    def conservative(cls) -> 'ArbConfig':
        """
        Conservative preset - prioritizes profit over volume.

        - Rotates every 2 hours
        - Smaller position sizes
        - Higher spread threshold
        """
        return cls(
            scan_interval=1800,  # 30 minutes
            rotation_interval=7200,  # 2 hours
            position_size_usd=50.0,  # $50 per leg
            max_total_position_usd=250.0,
            min_spread_threshold=10.0,  # More conservative
            close_spread_threshold=5.0,
            enable_rotation=True,
            rotation_jitter=600,
        )

    @classmethod
    def testing(cls) -> 'ArbConfig':
        """
        Testing preset - frequent checks, small sizes.
        """
        return cls(
            scan_interval=60,  # 1 minute
            rotation_interval=300,  # 5 minutes
            position_size_usd=10.0,  # $10 per leg
            max_total_position_usd=50.0,
            min_spread_threshold=1.0,  # Very low for testing
            close_spread_threshold=0.5,
            enable_rotation=True,
            rotation_jitter=30,
            dry_run=True,
        )
