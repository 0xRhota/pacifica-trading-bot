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
from typing import Optional, Dict, List

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
        # Regex patterns for parsing single decision
        self.decision_pattern = re.compile(
            r"DECISION:\s*(BUY|SELL|CLOSE|NOTHING)(?:\s+(\w+))?",
            re.IGNORECASE
        )
        self.confidence_pattern = re.compile(
            r"CONFIDENCE:\s*([0-9.]+)",
            re.IGNORECASE
        )
        self.reason_pattern = re.compile(
            r"REASON:\s*(.+)",
            re.IGNORECASE | re.DOTALL
        )
        # Regex pattern for parsing multiple decisions (new format)
        self.token_pattern = re.compile(
            r"TOKEN:\s*(\w+)",
            re.IGNORECASE
        )
        self.multi_decision_pattern = re.compile(
            r"TOKEN:\s*(\w+)\s*\n\s*DECISION:\s*(BUY|SELL|CLOSE|NOTHING)(?:\s+(\w+))?\s*\n\s*CONFIDENCE:\s*([0-9.]+)\s*\n\s*REASON:\s*(.+?)(?=\n\s*TOKEN:|$)",
            re.IGNORECASE | re.DOTALL | re.MULTILINE
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

        # Extract CONFIDENCE (optional, defaults to 0.5 if not found)
        confidence_match = self.confidence_pattern.search(response)
        if confidence_match:
            try:
                confidence = float(confidence_match.group(1))
                # Clamp between 0.3 and 1.0
                confidence = max(0.3, min(1.0, confidence))
            except ValueError:
                confidence = 0.5  # Default medium confidence
        else:
            confidence = 0.5  # Default medium confidence if not specified

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

        logger.info(f"✅ Parsed: {action} {symbol or ''} | Confidence: {confidence:.2f} | Reason: {reason[:50]}...")

        return {
            "action": action,
            "symbol": symbol,
            "reason": reason,
            "confidence": confidence
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

    def parse_multiple_decisions(self, response: str) -> Optional[List[Dict]]:
        """
        Parse multiple trading decisions from LLM response (one per analyzed token)
        
        Args:
            response: Raw LLM response string with multiple decision blocks
            
        Returns:
            List of decision dicts, each with keys: action, symbol, reason, confidence
            None if parsing failed
        """
        if not response or not isinstance(response, str):
            logger.error("Invalid response: empty or not string")
            return None
        
        # Clean response
        response = response.strip()
        
        decisions = []
        
        # Try to parse using the multi-decision pattern first
        matches = self.multi_decision_pattern.finditer(response)
        found_any = False
        
        for match in matches:
            found_any = True
            token = match.group(1).upper()
            action = match.group(2).upper()
            symbol_in_decision = match.group(3).upper() if match.group(3) else None
            confidence_str = match.group(4)
            reason = match.group(5).strip()
            
            # Use symbol from TOKEN line if not in DECISION line
            symbol = symbol_in_decision or token
            
            # Validate action
            if action not in ["BUY", "SELL", "CLOSE", "NOTHING"]:
                logger.warning(f"Invalid action for {token}: {action}")
                continue
            
            # Validate symbol
            if action in ["BUY", "SELL", "CLOSE"]:
                if not symbol:
                    logger.warning(f"Missing symbol for {action} decision for {token}")
                    continue
                if symbol not in self.VALID_SYMBOLS:
                    logger.warning(f"Invalid symbol: {symbol} (not in Pacifica markets)")
                    continue
            
            # Parse confidence
            try:
                confidence = float(confidence_str)
                confidence = max(0.3, min(1.0, confidence))
            except (ValueError, TypeError):
                confidence = 0.5  # Default medium confidence
            
            # Validate symbol for NOTHING
            if action == "NOTHING":
                symbol = None
            
            decisions.append({
                "action": action,
                "symbol": symbol,
                "reason": reason,
                "confidence": confidence
            })
            
            logger.info(f"✅ Parsed decision for {token}: {action} {symbol or ''} | Confidence: {confidence:.2f}")
        
        # If we didn't find any matches with the new format, try fallback to single decision
        if not found_any:
            logger.warning("No multi-decision format found, trying single decision fallback...")
            single_decision = self.parse_response(response)
            if single_decision:
                decisions = [single_decision]
            else:
                logger.error("Failed to parse any decisions from response")
                return None
        
        if not decisions:
            logger.error("No valid decisions parsed from response")
            return None
        
        logger.info(f"✅ Parsed {len(decisions)} decisions from response")
        return decisions
