"""
LLM Response Parser
Parses and validates LLM trading decisions with strict regex validation

Expected format:
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | NOTHING]
REASON: [Reasoning in 2-3 sentences]

Usage:
    parser = ResponseParser()
    result = parser.parse_response(llm_response)
    if result:
        action = result['action']  # BUY, SELL, or NOTHING
        symbol = result['symbol']  # Symbol or None
        reason = result['reason']  # Reasoning text
"""

import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse and validate LLM trading decisions"""

    # Valid Pacifica symbols
    VALID_SYMBOLS = [
        "ETH", "BTC", "SOL", "PUMP", "XRP", "HYPE", "DOGE", "FARTCOIN",
        "ENA", "BNB", "SUI", "kBONK", "PENGU", "AAVE", "LINK", "kPEPE",
        "LTC", "LDO", "UNI", "CRV", "WLFI", "AVAX", "ASTER", "XPL",
        "2Z", "PAXG", "ZEC", "MON"
    ]

    def __init__(self):
        """Initialize response parser"""
        # Regex patterns for parsing
        self.decision_pattern = re.compile(
            r"DECISION:\s*(BUY|SELL|CLOSE|NOTHING)(?:\s+(\w+))?",
            re.IGNORECASE
        )
        self.reason_pattern = re.compile(
            r"REASON:\s*(.+)",
            re.IGNORECASE | re.DOTALL
        )

    def parse_response(self, response: str) -> Optional[Dict]:
        """
        Parse LLM response with strict validation

        Args:
            response: Raw LLM response string

        Returns:
            Dict with keys: action, symbol, reason
            None if parsing failed
        """
        if not response or not isinstance(response, str):
            logger.error("Invalid response: empty or not string")
            return None

        # Clean response
        response = response.strip()

        # Extract DECISION
        decision_match = self.decision_pattern.search(response)
        if not decision_match:
            logger.error(f"Failed to parse DECISION from response: {response[:200]}")
            return None

        action = decision_match.group(1).upper()
        symbol = decision_match.group(2).upper() if decision_match.group(2) else None

        # Validate action
        if action not in ["BUY", "SELL", "CLOSE", "NOTHING"]:
            logger.error(f"Invalid action: {action}")
            return None

        # Validate symbol (required for BUY/SELL/CLOSE)
        if action in ["BUY", "SELL", "CLOSE"]:
            if not symbol:
                logger.error(f"Missing symbol for {action} decision")
                return None

            if symbol not in self.VALID_SYMBOLS:
                logger.error(f"Invalid symbol: {symbol} (not in Pacifica markets)")
                return None

        # Symbol should be None for NOTHING
        if action == "NOTHING":
            symbol = None

        # Extract REASON
        reason_match = self.reason_pattern.search(response)
        if not reason_match:
            logger.warning("Failed to parse REASON from response (using empty)")
            reason = ""
        else:
            reason = reason_match.group(1).strip()

        # Validate reason (should have some content)
        if not reason:
            logger.warning("Empty REASON provided")

        logger.info(f"✅ Parsed: {action} {symbol or ''} | Reason: {reason[:50]}...")

        return {
            "action": action,
            "symbol": symbol,
            "reason": reason
        }

    def validate_decision(
        self,
        parsed: Dict,
        open_positions: list,
        max_positions: int = 3
    ) -> tuple[bool, Optional[str]]:
        """
        Validate parsed decision against current state

        Args:
            parsed: Parsed response dict
            open_positions: List of current open positions
            max_positions: Max allowed open positions (default: 3)

        Returns:
            (is_valid, error_message)
        """
        action = parsed.get("action")
        symbol = parsed.get("symbol")

        # NOTHING is always valid
        if action == "NOTHING":
            return True, None

        # CLOSE requires existing position
        if action == "CLOSE":
            pos_exists = any(pos.get("symbol") == symbol for pos in open_positions)
            if not pos_exists:
                return False, f"No open position to close for {symbol}"
            return True, None

        # BUY/SELL validation
        # Check position limit
        if len(open_positions) >= max_positions:
            return False, f"Max positions ({max_positions}) already open"

        # Check for conflicting positions
        for pos in open_positions:
            pos_symbol = pos.get("symbol")

            if pos_symbol == symbol:
                return False, f"Already have open position in {symbol}"

        return True, None

    def parse_with_retries(
        self,
        responses: list[str],
        open_positions: list,
        max_positions: int = 3
    ) -> Optional[Dict]:
        """
        Parse multiple LLM responses (from retries) and return first valid one

        Args:
            responses: List of LLM response strings
            open_positions: Current open positions
            max_positions: Max allowed positions

        Returns:
            First valid parsed decision or None
        """
        for i, response in enumerate(responses):
            logger.info(f"Parsing response attempt {i + 1}/{len(responses)}...")

            parsed = self.parse_response(response)
            if parsed is None:
                continue

            # Validate decision
            is_valid, error = self.validate_decision(parsed, open_positions, max_positions)
            if is_valid:
                return parsed
            else:
                logger.warning(f"Decision validation failed: {error}")

        logger.error("All response parse attempts failed")
        return None
