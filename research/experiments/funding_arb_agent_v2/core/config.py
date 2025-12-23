"""
LLM Funding Arbitrage Configuration
====================================
Configuration for the LLM-driven delta-neutral funding rate arbitrage bot.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class LLMFundingArbConfig:
    """Configuration for LLM-driven funding rate arbitrage"""

    # ===== TIMING =====
    scan_interval: int = 300  # 5 minutes between scans

    # ===== POSITION SIZING (Code-Enforced) =====
    max_position_pct: float = 0.80  # Use 80% of smaller account balance
    max_position_usd: float = 100.0  # Hard cap per leg
    min_position_usd: float = 10.0   # Minimum viable position

    # ===== SPREAD THRESHOLDS =====
    min_spread_annualized: float = 5.0   # Minimum 5% annualized to enter
    close_spread_threshold: float = 2.0  # Close if spread drops below 2%

    # ===== LLM SETTINGS =====
    model: str = "qwen-max"  # qwen-max or deepseek-chat
    temperature: float = 0.1  # Low for consistency
    min_confidence: float = 0.70  # Only act if confidence > 70%
    max_tokens: int = 1500

    # ===== CIRCUIT BREAKERS (Code-Enforced) =====
    max_volatility_1h: float = 5.0   # Pause if 1h volatility > 5%
    max_position_age_hours: float = 12.0  # Force rotate after 12 hours
    max_spread_reversal_pct: float = 50.0  # Close if spread reverses by 50%

    # ===== EXECUTION =====
    dry_run: bool = True
    execution_timeout: int = 30  # Seconds to wait for order fill
    rollback_on_partial: bool = True  # Always rollback if one leg fails

    # ===== CHURN MODE (Volume Farming) =====
    churn_mode: bool = False  # Enable close/reopen every cycle for volume
    multi_asset: bool = False  # Allow multiple simultaneous positions
    funding_protection_minutes: int = 10  # Don't close within X minutes of funding time

    # ===== FUNDING TIMES (UTC hours) =====
    # Most perp DEXs settle funding at 00:00, 08:00, 16:00 UTC
    funding_times_utc: List[int] = field(default_factory=lambda: [0, 8, 16])

    # ===== SYMBOLS =====
    symbols: List[str] = field(default_factory=lambda: ["BTC", "ETH", "SOL"])

    # ===== SYMBOL MAPPINGS =====
    # Maps normalized symbol to exchange-specific format
    hibachi_symbols: dict = field(default_factory=lambda: {
        "BTC": "BTC/USDT-P",
        "ETH": "ETH/USDT-P",
        "SOL": "SOL/USDT-P"
    })
    extended_symbols: dict = field(default_factory=lambda: {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "SOL": "SOL-USD"
    })

    # ===== LOGGING =====
    log_file: str = "logs/funding_arb_llm.log"
    log_level: str = "INFO"

    def __post_init__(self):
        """Validate configuration"""
        assert self.scan_interval >= 60, "Scan interval must be at least 60 seconds"
        assert self.max_position_pct <= 1.0, "Max position pct must be <= 1.0"
        assert self.min_spread_annualized > self.close_spread_threshold
        assert self.min_confidence >= 0.5, "Min confidence should be at least 0.5"

    @classmethod
    def testing(cls) -> 'LLMFundingArbConfig':
        """Testing preset with small sizes and short intervals"""
        return cls(
            scan_interval=60,
            max_position_usd=20.0,
            min_spread_annualized=1.0,
            close_spread_threshold=0.5,
            dry_run=True,
            log_file="logs/funding_arb_llm_test.log"
        )

    @classmethod
    def conservative(cls) -> 'LLMFundingArbConfig':
        """Conservative preset - higher thresholds"""
        return cls(
            scan_interval=600,  # 10 minutes
            max_position_usd=50.0,
            min_spread_annualized=10.0,
            close_spread_threshold=5.0,
            min_confidence=0.80,
            dry_run=False
        )

    @classmethod
    def churn(cls) -> 'LLMFundingArbConfig':
        """Churn preset - maximize volume while capturing funding"""
        return cls(
            scan_interval=300,  # 5 minutes
            max_position_pct=0.95,  # Use 95% of smaller account balance
            max_position_usd=200.0,  # Higher cap per leg
            min_spread_annualized=3.0,  # Lower threshold to open more positions
            close_spread_threshold=1.0,
            min_confidence=0.60,
            churn_mode=True,  # Close/reopen every cycle
            multi_asset=True,  # Multiple positions
            funding_protection_minutes=10,  # Protect funding capture
            dry_run=False,
            log_file="logs/funding_arb_churn.log"
        )
