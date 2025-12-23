"""
Response Parser for LLM Funding Arbitrage
==========================================
Parses and validates LLM responses for funding arbitrage decisions.
"""

import json
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class ArbDecision:
    """Parsed arbitrage decision from LLM"""
    action: str  # OPEN, CLOSE, ROTATE, HOLD
    asset: Optional[str]  # BTC, ETH, SOL (None for HOLD)
    hibachi_direction: Optional[str]  # SHORT or LONG
    extended_direction: Optional[str]  # SHORT or LONG
    reasoning: str
    confidence: float
    raw_response: str

    @property
    def is_valid(self) -> bool:
        """Check if decision is valid"""
        if self.action == "HOLD":
            return True

        if self.action in ["OPEN", "CLOSE", "ROTATE"]:
            # Must have asset and directions
            if not self.asset:
                return False
            if self.action != "CLOSE":
                # OPEN and ROTATE need directions
                if not self.hibachi_direction or not self.extended_direction:
                    return False
                # Directions must be opposite
                if self.hibachi_direction == self.extended_direction:
                    return False
            return True

        return False

    @property
    def is_delta_neutral(self) -> bool:
        """Check if directions are delta neutral"""
        if self.action == "HOLD":
            return True
        if self.action == "CLOSE":
            return True  # Closing is always fine
        if not self.hibachi_direction or not self.extended_direction:
            return False
        return self.hibachi_direction != self.extended_direction


class ResponseParser:
    """Parses LLM responses into structured decisions"""

    def __init__(self, config):
        self.config = config

    def parse(self, response: str) -> Optional[ArbDecision]:
        """
        Parse LLM response into ArbDecision.

        Args:
            response: Raw LLM response string

        Returns:
            ArbDecision if parsing successful, None otherwise
        """
        try:
            # Try to extract JSON from response
            json_data = self._extract_json(response)

            if not json_data:
                logger.warning("Could not extract JSON from response")
                return self._fallback_parse(response)

            # Parse fields
            action = json_data.get("action", "").upper()
            asset = json_data.get("asset", "").upper() if json_data.get("asset") else None
            reasoning = json_data.get("reasoning", "No reasoning provided")
            confidence = float(json_data.get("confidence", 0.5))

            # Parse directions
            direction = json_data.get("direction", {})
            hibachi_dir = direction.get("hibachi", "").upper() if direction else None
            extended_dir = direction.get("extended", "").upper() if direction else None

            # Validate action
            if action not in ["OPEN", "CLOSE", "ROTATE", "HOLD"]:
                logger.warning(f"Invalid action: {action}")
                return None

            # Validate asset
            if asset and asset not in self.config.symbols:
                logger.warning(f"Invalid asset: {asset}")
                asset = None

            # Validate directions
            if hibachi_dir and hibachi_dir not in ["LONG", "SHORT"]:
                hibachi_dir = None
            if extended_dir and extended_dir not in ["LONG", "SHORT"]:
                extended_dir = None

            # Clamp confidence
            confidence = max(0.0, min(1.0, confidence))

            decision = ArbDecision(
                action=action,
                asset=asset,
                hibachi_direction=hibachi_dir,
                extended_direction=extended_dir,
                reasoning=reasoning,
                confidence=confidence,
                raw_response=response
            )

            # Validate
            if not decision.is_valid:
                logger.warning(f"Decision validation failed: {decision}")
                return None

            if not decision.is_delta_neutral:
                logger.error(f"Decision is NOT delta neutral! {hibachi_dir} / {extended_dir}")
                return None

            return decision

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None

    def _extract_json(self, response: str) -> Optional[Dict]:
        """Extract JSON from response text"""
        # Try to find JSON block
        patterns = [
            r'```json\s*(.*?)\s*```',  # Markdown code block
            r'```\s*(.*?)\s*```',  # Generic code block
            r'\{[^{}]*"action"[^{}]*\}',  # Direct JSON object
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_str = match.group(1) if '```' in pattern else match.group(0)
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue

        # Try parsing entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        return None

    def _fallback_parse(self, response: str) -> Optional[ArbDecision]:
        """
        Fallback parsing when JSON extraction fails.
        Tries to extract decision from natural language.
        """
        response_upper = response.upper()

        # Detect action
        action = None
        if "HOLD" in response_upper or "NO TRADE" in response_upper or "NO_TRADE" in response_upper:
            action = "HOLD"
        elif "CLOSE" in response_upper:
            action = "CLOSE"
        elif "ROTATE" in response_upper:
            action = "ROTATE"
        elif "OPEN" in response_upper or "ENTER" in response_upper:
            action = "OPEN"

        if not action:
            logger.warning("Could not determine action from response")
            return None

        # Detect asset
        asset = None
        for symbol in self.config.symbols:
            if symbol in response_upper:
                asset = symbol
                break

        # Detect directions
        hibachi_dir = None
        extended_dir = None

        if "SHORT HIBACHI" in response_upper or "HIBACHI SHORT" in response_upper:
            hibachi_dir = "SHORT"
        elif "LONG HIBACHI" in response_upper or "HIBACHI LONG" in response_upper:
            hibachi_dir = "LONG"

        if "SHORT EXTENDED" in response_upper or "EXTENDED SHORT" in response_upper:
            extended_dir = "SHORT"
        elif "LONG EXTENDED" in response_upper or "EXTENDED LONG" in response_upper:
            extended_dir = "LONG"

        # If one direction found, infer the other
        if hibachi_dir and not extended_dir:
            extended_dir = "LONG" if hibachi_dir == "SHORT" else "SHORT"
        elif extended_dir and not hibachi_dir:
            hibachi_dir = "LONG" if extended_dir == "SHORT" else "SHORT"

        return ArbDecision(
            action=action,
            asset=asset,
            hibachi_direction=hibachi_dir,
            extended_direction=extended_dir,
            reasoning=response[:500],  # Use response as reasoning
            confidence=0.6,  # Lower confidence for fallback
            raw_response=response
        )

    def validate_against_data(self, decision: ArbDecision, data) -> bool:
        """
        Validate decision against current market data.

        Checks:
        - Asset exists in spreads
        - Direction matches funding rate logic
        - Confidence meets threshold
        """
        if decision.action == "HOLD":
            return True

        # Check confidence threshold
        if decision.confidence < self.config.min_confidence:
            logger.warning(
                f"Confidence {decision.confidence:.2f} below threshold {self.config.min_confidence:.2f}"
            )
            return False

        # Check asset
        if decision.asset and decision.asset not in data.spreads:
            logger.warning(f"Asset {decision.asset} not in available spreads")
            return False

        # Check direction logic (SHORT should be on higher rate exchange)
        if decision.asset and decision.action in ["OPEN", "ROTATE"]:
            spread = data.spreads.get(decision.asset)
            if spread:
                expected_short = spread.short_exchange
                actual_short = "Hibachi" if decision.hibachi_direction == "SHORT" else "Extended"

                if actual_short != expected_short:
                    logger.warning(
                        f"Direction mismatch: LLM wants SHORT {actual_short}, "
                        f"but {expected_short} has higher rate"
                    )
                    # This is a warning, not a hard failure - LLM might have reasoning

        return True
