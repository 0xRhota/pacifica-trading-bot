"""LLM-Based Trading Strategy - Current strategy"""

import logging
from typing import Dict, List, Optional
from strategies.base_strategy import BaseStrategy
from core.decision_engine import DecisionEngine
from llm_agent.llm.model_client import ModelClient
from llm_agent.llm.prompt_formatter import PromptFormatter
from llm_agent.llm.response_parser import ResponseParser

logger = logging.getLogger(__name__)


class LLMStrategy(BaseStrategy):
    """LLM-based strategy - current strategy"""
    
    def __init__(self, deepseek_api_key: str, cambrian_api_key: str, max_positions: int = 15, logger_instance=None):
        self.model_client = ModelClient(
            api_key=deepseek_api_key,
            model="deepseek-chat",
            max_retries=2,
            daily_spend_limit=10.0
        )
        self.prompt_formatter = PromptFormatter()
        self.response_parser = ResponseParser()
        self.logger_instance = logger_instance  # Store for DecisionEngine
        self.decision_engine = DecisionEngine(
            self.model_client,
            self.prompt_formatter,
            self.response_parser,
            logger_instance=logger_instance  # Pass logger to DecisionEngine
        )
        self.max_positions = max_positions
    
    async def get_decisions(self, market_data: Dict, positions: List[Dict], context: Dict) -> List[Dict]:
        """Get decisions from LLM"""
        context['max_positions'] = self.max_positions
        decisions = await self.decision_engine.get_decisions(market_data, positions, context)
        
        # Log summary if no decisions
        if not decisions:
            log_msg = f"No LLM decisions | Markets: {len(market_data)} | Positions: {len(positions)}"
            if self.logger_instance:
                self.logger_instance.info(log_msg, component="llm_strategy")
            else:
                logger.info(log_msg)
        
        return decisions


