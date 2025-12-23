"""
Cambrian Perp Risk Engine Client
Calculates liquidation risk using Monte Carlo simulation with historical data

API Docs: https://docs.cambrian.org/api/v1/perp-risk-engine
"""

import logging
import requests
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Risk assessment result from Cambrian API"""
    # Core risk metrics
    risk_probability: float      # 0.0-1.0 probability of liquidation
    liquidation_price: float     # Price at which position liquidates
    entry_price: float           # Entry price used for calculation
    price_change_needed: float   # % change needed to hit liquidation
    sigmas_away: float           # Standard deviations from liquidation

    # Volatility data
    volatility: float            # Historical volatility coefficient
    drift: float                 # Price drift/trend

    # Simulation details
    total_simulations: int       # Number of Monte Carlo paths
    liquidated_paths: int        # Paths that hit liquidation
    data_points_used: int        # Historical data points analyzed
    risk_horizon: str            # Time horizon (1h, 1d, 1w, 1mo)

    # Input parameters
    leverage: float
    direction: str               # "long" or "short"
    symbol: str

    @property
    def risk_level(self) -> str:
        """Categorize risk level"""
        if self.risk_probability < 0.01:
            return "VERY_LOW"
        elif self.risk_probability < 0.05:
            return "LOW"
        elif self.risk_probability < 0.10:
            return "MODERATE"
        elif self.risk_probability < 0.20:
            return "HIGH"
        else:
            return "EXTREME"

    @property
    def risk_emoji(self) -> str:
        """Get emoji for risk level"""
        return {
            "VERY_LOW": "✅",
            "LOW": "🟢",
            "MODERATE": "🟡",
            "HIGH": "🟠",
            "EXTREME": "🔴"
        }.get(self.risk_level, "❓")

    def to_prompt_string(self) -> str:
        """Format for LLM prompt injection"""
        return f"""RISK ASSESSMENT ({self.symbol} {self.leverage}x {self.direction.upper()}):
  Liquidation Risk: {self.risk_probability*100:.2f}% ({self.risk_level})
  Liquidation Price: ${self.liquidation_price:.2f}
  Price Change to Liq: {self.price_change_needed*100:+.1f}%
  Sigmas from Liq: {self.sigmas_away:.1f}σ
  Volatility: {self.volatility*100:.1f}%
  Verdict: {self.risk_emoji} {self.risk_level}"""

    def to_log_string(self) -> str:
        """Format for logging"""
        return (
            f"{self.risk_emoji} {self.symbol} {self.leverage}x {self.direction.upper()} | "
            f"Risk: {self.risk_probability*100:.2f}% | "
            f"Liq@${self.liquidation_price:.2f} ({self.price_change_needed*100:+.1f}%) | "
            f"{self.sigmas_away:.1f}σ away | "
            f"Vol: {self.volatility*100:.0f}%"
        )


class CambrianRiskEngine:
    """
    Client for Cambrian Perp Risk Engine API

    Uses Monte Carlo simulation to calculate liquidation probability
    for leveraged perpetual positions.
    """

    API_URL = "https://risk.cambrian.network/api/v1/perp-risk-engine"

    # Token addresses for common assets
    TOKEN_ADDRESSES = {
        "SOL": "So11111111111111111111111111111111111111112",
        "BTC": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",  # Wrapped BTC on Solana
        "ETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # Wrapped ETH on Solana
        "WBTC": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
        "WETH": "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",
    }

    # Risk thresholds for trade decisions
    MAX_ACCEPTABLE_RISK = 0.10       # 10% - block trades above this
    HIGH_RISK_THRESHOLD = 0.05       # 5% - reduce position size
    MODERATE_RISK_THRESHOLD = 0.02   # 2% - log warning

    def __init__(self, api_key: str):
        """
        Initialize risk engine client

        Args:
            api_key: Cambrian API key
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })

        logger.info("=" * 60)
        logger.info("CAMBRIAN RISK ENGINE INITIALIZED")
        logger.info(f"  API: {self.API_URL}")
        logger.info(f"  Max Acceptable Risk: {self.MAX_ACCEPTABLE_RISK*100:.0f}%")
        logger.info(f"  High Risk Threshold: {self.HIGH_RISK_THRESHOLD*100:.0f}%")
        logger.info("=" * 60)

    def get_token_address(self, symbol: str) -> Optional[str]:
        """Get Solana token address for symbol"""
        # Normalize symbol (remove -USD, /USDT-P, etc.)
        clean_symbol = symbol.upper().replace("-USD", "").replace("/USDT-P", "").replace("-PERP", "")
        return self.TOKEN_ADDRESSES.get(clean_symbol)

    def assess_risk(
        self,
        symbol: str,
        entry_price: float,
        leverage: float,
        direction: str,
        risk_horizon: str = "1d"
    ) -> Optional[RiskAssessment]:
        """
        Assess liquidation risk for a potential position

        Args:
            symbol: Trading symbol (e.g., "SOL", "BTC/USDT-P", "ETH-USD")
            entry_price: Entry price in USD
            leverage: Leverage multiplier (1-1000)
            direction: "long" or "short"
            risk_horizon: Time horizon - "1h", "1d", "1w", "1mo"

        Returns:
            RiskAssessment object or None if API fails
        """
        # Get token address
        token_address = self.get_token_address(symbol)
        if not token_address:
            logger.warning(f"[RISK] No token address for {symbol}, skipping risk check")
            return None

        # Normalize direction
        direction = direction.lower()
        if direction in ["buy", "long"]:
            direction = "long"
        elif direction in ["sell", "short"]:
            direction = "short"

        try:
            params = {
                "token_address": token_address,
                "entry_price": entry_price,
                "leverage": leverage,
                "direction": direction,
                "risk_horizon": risk_horizon
            }

            response = self.session.get(self.API_URL, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"[RISK] API error {response.status_code}: {response.text[:200]}")
                return None

            data = response.json()

            if data.get("status") != "success":
                logger.error(f"[RISK] API returned error: {data}")
                return None

            # Parse simulation details
            sim_details = data.get("simulationDetails", {})

            assessment = RiskAssessment(
                risk_probability=data.get("riskProbability", 0),
                liquidation_price=data.get("liquidationPrice", 0),
                entry_price=data.get("entryPrice", entry_price),
                price_change_needed=data.get("priceChangeNeeded", 0),
                sigmas_away=data.get("sigmasAway", 0),
                volatility=data.get("volatility", 0),
                drift=data.get("drift", 0),
                total_simulations=sim_details.get("totalSimulations", 0),
                liquidated_paths=sim_details.get("liquidatedPaths", 0),
                data_points_used=sim_details.get("dataPointsUsed", 0),
                risk_horizon=risk_horizon,
                leverage=leverage,
                direction=direction,
                symbol=symbol
            )

            return assessment

        except requests.exceptions.Timeout:
            logger.error(f"[RISK] API timeout for {symbol}")
            return None
        except Exception as e:
            logger.error(f"[RISK] Error assessing risk for {symbol}: {e}")
            return None

    def should_block_trade(self, assessment: RiskAssessment) -> Tuple[bool, str]:
        """
        Determine if a trade should be blocked based on risk

        Returns:
            (should_block, reason)
        """
        if assessment.risk_probability >= self.MAX_ACCEPTABLE_RISK:
            return True, f"Risk too high: {assessment.risk_probability*100:.1f}% > {self.MAX_ACCEPTABLE_RISK*100:.0f}% threshold"

        if assessment.sigmas_away < 1.5:
            return True, f"Too close to liquidation: {assessment.sigmas_away:.1f}σ (need >1.5σ)"

        return False, "Risk acceptable"

    def get_position_size_multiplier(self, assessment: RiskAssessment) -> float:
        """
        Get position size multiplier based on risk

        Returns:
            Multiplier (0.0-1.0) to apply to position size
        """
        if assessment.risk_probability >= self.MAX_ACCEPTABLE_RISK:
            return 0.0  # Block trade

        if assessment.risk_probability >= self.HIGH_RISK_THRESHOLD:
            # Scale down: 5% risk = 0.5x, 10% risk = 0x
            scale = 1.0 - ((assessment.risk_probability - self.HIGH_RISK_THRESHOLD) /
                          (self.MAX_ACCEPTABLE_RISK - self.HIGH_RISK_THRESHOLD))
            return max(0.25, min(0.5, scale))  # 25-50% of normal size

        if assessment.risk_probability >= self.MODERATE_RISK_THRESHOLD:
            # Slight reduction: 2% risk = 0.9x, 5% risk = 0.5x
            scale = 1.0 - ((assessment.risk_probability - self.MODERATE_RISK_THRESHOLD) /
                          (self.HIGH_RISK_THRESHOLD - self.MODERATE_RISK_THRESHOLD)) * 0.5
            return max(0.5, scale)  # 50-100% of normal size

        return 1.0  # Full size

    def log_assessment(self, assessment: RiskAssessment) -> None:
        """Log a detailed risk assessment"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 CAMBRIAN RISK ASSESSMENT")
        logger.info("=" * 70)
        logger.info(f"  Symbol: {assessment.symbol}")
        logger.info(f"  Direction: {assessment.direction.upper()}")
        logger.info(f"  Leverage: {assessment.leverage}x")
        logger.info(f"  Entry Price: ${assessment.entry_price:.2f}")
        logger.info(f"  Risk Horizon: {assessment.risk_horizon}")
        logger.info("")
        logger.info(f"  {assessment.risk_emoji} LIQUIDATION RISK: {assessment.risk_probability*100:.2f}% ({assessment.risk_level})")
        logger.info(f"  📍 Liquidation Price: ${assessment.liquidation_price:.2f}")
        logger.info(f"  📉 Price Change to Liq: {assessment.price_change_needed*100:+.1f}%")
        logger.info(f"  📐 Sigmas Away: {assessment.sigmas_away:.1f}σ")
        logger.info("")
        logger.info(f"  📈 Volatility: {assessment.volatility*100:.1f}%")
        logger.info(f"  📊 Drift: {assessment.drift*100:+.1f}%")
        logger.info(f"  🎲 Simulations: {assessment.total_simulations:,} paths, {assessment.liquidated_paths} liquidated")
        logger.info(f"  📅 Data Points: {assessment.data_points_used}")
        logger.info("=" * 70)
        logger.info("")


# Convenience function for quick risk check
def quick_risk_check(
    api_key: str,
    symbol: str,
    price: float,
    leverage: float,
    direction: str
) -> Optional[Dict]:
    """
    Quick one-off risk check without instantiating client

    Returns dict with key metrics or None
    """
    engine = CambrianRiskEngine(api_key)
    assessment = engine.assess_risk(symbol, price, leverage, direction)

    if not assessment:
        return None

    return {
        "risk_pct": assessment.risk_probability * 100,
        "liq_price": assessment.liquidation_price,
        "price_change_pct": assessment.price_change_needed * 100,
        "sigmas": assessment.sigmas_away,
        "volatility_pct": assessment.volatility * 100,
        "risk_level": assessment.risk_level,
        "should_trade": assessment.risk_probability < 0.10
    }
