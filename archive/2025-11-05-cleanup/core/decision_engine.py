"""Decision Engine - Strategy-agnostic LLM decision making"""

import logging
from typing import Dict, List, Optional
from llm_agent.llm.model_client import ModelClient
from llm_agent.llm.prompt_formatter import PromptFormatter
from llm_agent.llm.response_parser import ResponseParser

# Configure logger to ensure it writes to file
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Ensure we capture all logs

# If no handler exists, add a handler (fallback - should be handled by UnifiedLogger)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class DecisionEngine:
    """LLM decision making - strategy-agnostic"""
    
    def __init__(self, model_client: ModelClient, prompt_formatter: PromptFormatter, response_parser: ResponseParser, logger_instance=None):
        self.model_client = model_client
        self.prompt_formatter = prompt_formatter
        self.response_parser = response_parser
        # Store UnifiedLogger instance to use its methods (not raw logger)
        self.unified_logger = logger_instance
        # Fallback to module logger if no UnifiedLogger provided
        self.logger = logger if logger_instance is None else logger_instance
    
    def _log(self, level: str, message: str):
        """Helper to log using UnifiedLogger or fallback logger"""
        if self.unified_logger:
            getattr(self.unified_logger, level)(message, component="decision_engine")
        else:
            getattr(logger, level)(message)
    
    async def get_decisions(self, market_data: Dict, positions: List[Dict], context: Dict) -> List[Dict]:
        """Get trading decisions from LLM"""
        # CRITICAL: Log entry point to confirm function is called
        self._log("info", f"🚀 DecisionEngine.get_decisions() called | Markets: {len(market_data)} | Positions: {len(positions)}")
        
        # Format prompt
        dex_name = context.get('dex_name')
        analyzed_tokens = context.get('analyzed_tokens', [])
        # Debug: Show full context keys to diagnose missing dex_name
        self._log("debug", f"🔍 Prompt formatting: dex_name={dex_name}, analyzed_tokens count={len(analyzed_tokens) if analyzed_tokens else 0}, context keys={list(context.keys())}")
        
        prompt = self.prompt_formatter.format_trading_prompt(
            macro_context=context.get('macro_context', ''),
            market_table=context.get('market_table', ''),
            open_positions=positions,
            deep42_context=context.get('deep42_context'),
            account_balance=context.get('account_balance', 0),
            hourly_review=context.get('hourly_review'),
            trade_history=context.get('trade_history', ''),
            recently_closed_symbols=context.get('recently_closed_symbols', []),
            analyzed_tokens=analyzed_tokens,
            dex_name=dex_name,  # Pass DEX name for dynamic prompts
            failed_executions=context.get('failed_executions')  # Pass failed executions for retry logic
        )
        
        # Log prompt summary
        self._log("info", f"📝 LLM Query: {len(prompt)} chars | Markets: {len(market_data)} | Positions: {len(positions)}")
        # Show full prompt in debug - no truncation (can be long, but that's OK for debugging)
        self._log("debug", f"Full prompt:\n{prompt}")
        
        # Query LLM with retries
        responses = []
        for attempt in range(self.model_client.max_retries + 1):
            self._log("debug", f"🤖 LLM Query attempt {attempt + 1}/{self.model_client.max_retries + 1}")
            
            result = self.model_client.query(
                prompt=prompt,
                max_tokens=500,
                temperature=0.1
            )
            
            if result is None:
                self._log("warning", f"❌ LLM query failed (attempt {attempt + 1})")
                continue
            
            llm_response = result["content"]
            self._log("info", f"✅ LLM Response ({len(llm_response)} chars): {llm_response[:200]}...")
            self._log("debug", f"Full LLM response: {llm_response}")
            
            responses.append(llm_response)
            
            # Parse decisions
            parsed_decisions = self.response_parser.parse_multiple_decisions(llm_response)
            self._log("info", f"📊 Parsed {len(parsed_decisions) if parsed_decisions else 0} decisions from LLM response")
            
            if parsed_decisions:
                self._log("debug", f"Parsed decisions: {parsed_decisions}")
                # Validate decisions
                validated = []
                invalid_count = 0
                for parsed in parsed_decisions:
                    is_valid, error = self.response_parser.validate_decision(
                        parsed,
                        open_positions=positions,
                        max_positions=context.get('max_positions', 15)
                    )
                    if is_valid:
                        validated.append({
                            "action": parsed.get("action", "").upper(),
                            "symbol": parsed.get("symbol", ""),
                            "reason": parsed.get("reason", ""),
                            "confidence": parsed.get("confidence", 0.5),
                            "cost": result.get("cost", 0)
                        })
                        self._log("info", f"✅ Valid decision: {parsed.get('action', '').upper()} {parsed.get('symbol', '')} | Confidence: {parsed.get('confidence', 0.5)} | Reason: {parsed.get('reason', '')[:100]}")
                    else:
                        invalid_count += 1
                        self._log("warning", f"❌ Invalid decision: {parsed} | Error: {error}")
                
                if validated:
                    self._log("info", f"🎯 Returning {len(validated)} validated decisions")
                    return validated
                else:
                    self._log("warning", f"⚠️ All {len(parsed_decisions)} parsed decisions failed validation")
            else:
                self._log("warning", f"❌ Failed to parse decisions from LLM response")
                self._log("debug", f"Response that failed to parse: {llm_response}")
            
            # Retry with clearer prompt
            if attempt < self.model_client.max_retries:
                self._log("info", f"🔄 Retrying with clearer prompt format (attempt {attempt + 1})")
                prompt += "\n\nIMPORTANT: Respond with decisions in this exact format:\nTOKEN: BTC\nDECISION: BUY BTC\nCONFIDENCE: 0.75\nREASON: Your reasoning here\n\n"
        
        self._log("warning", f"❌ No decisions after {self.model_client.max_retries + 1} attempts")
        return []


