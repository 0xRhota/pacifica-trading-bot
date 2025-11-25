"""
LLM Trading Agent
Main decision engine that orchestrates all LLM components

Usage:
    from llm_agent.data import MarketDataAggregator
    from llm_agent.llm import LLMTradingAgent

    aggregator = MarketDataAggregator(cambrian_api_key="...")
    agent = LLMTradingAgent(deepseek_api_key="...")

    # Get trading decision
    decision = agent.get_trading_decision(
        aggregator=aggregator,
        open_positions=[]
    )

    if decision:
        print(f"Action: {decision['action']}")
        print(f"Symbol: {decision['symbol']}")
        print(f"Reason: {decision['reason']}")
"""

import logging
from typing import Optional, Dict, List

from .model_client import ModelClient
from .response_parser import ResponseParser
from .deep42_tool import Deep42Tool
from .token_analysis_tool import TokenAnalysisTool
from ..config_prompts import get_prompt_formatter, get_active_strategy_info, PROMPT_STRATEGIES  # V2 config system (one level up)

logger = logging.getLogger(__name__)


class LLMTradingAgent:
    """Main LLM trading decision engine"""

    def __init__(
        self,
        deepseek_api_key: str,
        cambrian_api_key: str,
        model: str = "deepseek-chat",
        max_retries: int = 2,
        daily_spend_limit: float = 10.0,
        max_positions: int = 3,
        prompt_strategy: str = None  # Override config if specified
    ):
        """
        Initialize LLM trading agent

        Args:
            deepseek_api_key: DeepSeek API key (or OpenRouter key for qwen-max)
            cambrian_api_key: Cambrian API key for Deep42 queries
            model: Model name (default: deepseek-chat, qwen-max for Alpha Arena winner)
            max_retries: Number of retries on parse failure (default: 2)
            daily_spend_limit: Max USD to spend per day (default: $10)
            max_positions: Max open positions allowed (default: 3)
            prompt_strategy: Prompt strategy override (e.g., v8_pure_pnl)
        """
        self.max_retries = max_retries
        self.max_positions = max_positions

        # Initialize components
        self.model_client = ModelClient(
            api_key=deepseek_api_key,
            model=model,
            max_retries=max_retries,
            daily_spend_limit=daily_spend_limit
        )

        # V2: Use config system for prompt selection (easy rollback)
        # Can be overridden by prompt_strategy parameter
        if prompt_strategy and prompt_strategy in PROMPT_STRATEGIES:
            # Use specified strategy instead of config default
            import importlib
            strategy = PROMPT_STRATEGIES[prompt_strategy]
            module = importlib.import_module(strategy['file'])
            formatter_class = getattr(module, strategy['class'])

            # Check if strategy has a file to load
            strategy_file = strategy.get('strategy_file')
            if strategy_file:
                import os
                # Try to find the file relative to project root
                if not os.path.isabs(strategy_file):
                    # Assume relative to project root
                    import sys
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    strategy_file = os.path.join(project_root, strategy_file)

                self.prompt_formatter = formatter_class(strategy_file=strategy_file)
            else:
                self.prompt_formatter = formatter_class()

            logger.info(f"🎯 Active prompt strategy: {prompt_strategy} - {strategy['description']}")
        else:
            self.prompt_formatter = get_prompt_formatter()
            strategy_info = get_active_strategy_info()
            logger.info(f"🎯 Active prompt strategy: {strategy_info['version']} - {strategy_info['description']}")

        self.response_parser = ResponseParser()

        # Initialize Deep42 tool for macro market analysis
        self.deep42_tool = Deep42Tool(cambrian_api_key=cambrian_api_key)

        # Initialize token analysis tool for dynamic token discovery
        self.token_tool = TokenAnalysisTool(cambrian_api_key=cambrian_api_key)
        
        # Track recently selected tokens to encourage variety (keep last 20)
        self.recently_selected_tokens = []

        logger.info(f"✅ LLMTradingAgent initialized (model={model}, max_positions={max_positions})")

    def _get_deep42_context(self) -> str:
        """
        Get macro market state from Deep42

        Returns:
            Deep42's macro market analysis formatted for inclusion in trading prompt
        """
        logger.info("Getting Deep42 macro market state...")

        # Simple, focused question about macro market state
        from datetime import datetime
        today = datetime.now().strftime("%A, %B %d, %Y")
        question = f"What is the macro state of the crypto market today ({today})? Include overall market direction (up/down), sentiment, major trends, and key factors affecting the market."

        # Execute query against Deep42
        answer = self.deep42_tool.query(question)
        if not answer:
            return f"⚠️ Deep42 macro analysis unavailable"

        return f"""Deep42 Macro Market Analysis ({today}):
{answer}
"""

    def _select_tokens_to_analyze(self, available_tokens: List[str], num_tokens: int = 3) -> List[str]:
        """
        Ask LLM to select tokens to analyze in depth

        Args:
            available_tokens: List of available token symbols
            num_tokens: Number of tokens to select (default: 3)

        Returns:
            List of selected token symbols
        """
        import random
        from datetime import datetime

        today = datetime.now().strftime("%A, %B %d, %Y")

        # Shuffle available tokens to break deterministic ordering
        # This ensures the LLM sees different tokens at the top each time
        shuffled_tokens = available_tokens.copy()
        random.shuffle(shuffled_tokens)
        
        # Sample tokens for prompt (show shuffled list, up to 50)
        token_list = ", ".join(shuffled_tokens[:50])
        
        # Get recently selected tokens (last 20) to encourage variety
        recent_context = ""
        if self.recently_selected_tokens:
            recent_str = ", ".join(self.recently_selected_tokens[-10:])  # Last 10
            recent_context = f"\n\nRecently analyzed tokens (avoid repeating these unless they show strong new signals): {recent_str}"

        selection_prompt = f"""You are a crypto trading bot analyzing markets to make trading decisions.

Today's date: {today}

Available perpetual tokens (randomized order for variety):
{token_list}
{recent_context}

Your task: Select {num_tokens} tokens that you want to analyze in depth before making your trading decision.

CRITICAL: Choose DIFFERENT tokens than you've analyzed recently unless you see compelling new signals. Prioritize variety and explore new opportunities.

Guidelines:
- Select tokens with interesting price action, recent news, or catalysts
- Mix major assets (BTC, ETH, SOL) with altcoins for diversification
- Think about what's trending or has volatility potential
- EXPLORE NEW TOKENS - avoid defaulting to the same ones every time
- Only repeat recently analyzed tokens if you see STRONG new signals

Respond with ONLY the {num_tokens} token symbols separated by commas, no other text.
Example: PUMP, DOGE, ENA"""

        try:
            result = self.model_client.query(
                prompt=selection_prompt,
                max_tokens=50,
                temperature=0.8  # Increased from 0.4 to 0.8 for more variety and creativity
            )

            if result is None:
                logger.warning("Failed to get token selection from LLM")
                # Use shuffled list instead of deterministic top tokens
                selected = shuffled_tokens[:num_tokens]
            else:
                # Parse response (expect: "BTC, ETH, SOL")
                response = result["content"].strip()
                selected = [s.strip() for s in response.split(",")]
                selected = [s for s in selected if s]  # Remove empty strings
                selected = [s for s in selected if s in available_tokens]  # Validate tokens
                
                # If LLM returned invalid tokens, fill with shuffled available tokens
                if len(selected) < num_tokens:
                    remaining = [t for t in shuffled_tokens if t not in selected][:num_tokens - len(selected)]
                    selected.extend(remaining)

            # Track selected tokens for future variety
            self.recently_selected_tokens.extend(selected)
            if len(self.recently_selected_tokens) > 20:
                self.recently_selected_tokens = self.recently_selected_tokens[-20:]  # Keep last 20

            logger.info(f"LLM selected tokens: {selected}")
            return selected[:num_tokens]

        except Exception as e:
            logger.error(f"Error selecting tokens: {e}")
            # Use shuffled list as fallback
            return shuffled_tokens[:num_tokens]

    def _get_token_analyses(self, tokens: List[str]) -> str:
        """
        Get Deep42 analysis for selected tokens

        Args:
            tokens: List of token symbols to analyze

        Returns:
            Formatted token analyses for prompt
        """
        logger.info(f"Getting Deep42 analyses for {len(tokens)} tokens...")

        analyses = []
        for token in tokens:
            analysis = self.token_tool.analyze_token(token)
            if analysis:
                analyses.append(f"""--- {token} Analysis (Deep42/Cambrian) ---
{analysis}
""")
            else:
                analyses.append(f"--- {token} Analysis ---\n⚠️ Analysis unavailable\n")

        if not analyses:
            return ""

        return f"""
Selected Token Deep Dives:
{"".join(analyses)}
"""

    def _get_position_evaluations(self, open_positions: List[Dict]) -> str:
        """
        Get Deep42 evaluation of open positions

        Args:
            open_positions: List of open position dicts

        Returns:
            Formatted position evaluations for prompt
        """
        if not open_positions:
            return ""

        logger.info(f"Getting Deep42 evaluations for {len(open_positions)} positions...")

        evaluations = []
        for pos in open_positions:
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            entry = pos.get('entry_price', 0)
            current = pos.get('current_price', 0)
            time_held = pos.get('time_held', 'N/A')

            evaluation = self.token_tool.evaluate_position(
                symbol=symbol,
                entry_price=entry,
                current_price=current,
                side=side,
                time_held=time_held
            )

            if evaluation:
                evaluations.append(f"""--- {symbol} {side} Position Evaluation (Deep42/Cambrian) ---
Entry: ${entry:.2f}, Current: ${current:.2f}, Time: {time_held}
{evaluation}
""")
            else:
                evaluations.append(f"--- {symbol} {side} Position ---\n⚠️ Evaluation unavailable\n")

        if not evaluations:
            return ""

        return f"""
Open Position Evaluations:
{"".join(evaluations)}
"""

    def get_trading_decision(
        self,
        aggregator,  # MarketDataAggregator instance
        open_positions: Optional[List[Dict]] = None,
        force_macro_refresh: bool = False,
        trade_tracker=None,  # TradeTracker instance
        recently_closed_symbols: Optional[List[str]] = None,  # Symbols closed in last 2h
        account_balance: Optional[float] = None,  # Account balance in USD
        hourly_review: Optional[str] = None  # Hourly deep research review
    ) -> Optional[List[Dict]]:
        """
        Get trading decisions from LLM (one per analyzed token)

        Args:
            aggregator: MarketDataAggregator instance with fetched data
            open_positions: Current open positions (default: [])
            force_macro_refresh: Force refresh macro context (default: False)

        Returns:
            List of decision dicts, each with keys: action, symbol, reason, confidence, cost
            None if decision failed
        """
        if open_positions is None:
            open_positions = []

        logger.info(f"Getting trading decision (open positions: {len(open_positions)})...")

        # Step 1: Get macro market state from Deep42
        deep42_context = self._get_deep42_context()

        # Step 2: Get macro context (cached or fresh)
        logger.info("Fetching macro context...")
        macro_context = aggregator.get_macro_context(force_refresh=force_macro_refresh)

        # Step 3: Fetch market data for ALL Pacifica symbols with full technical indicators
        logger.info("Fetching market data for ALL Pacifica markets with indicators...")
        market_data = aggregator.fetch_all_markets()
        
        # Get all available Pacifica symbols from the market data
        all_symbols = list(market_data.keys())
        logger.info(f"Analyzing ALL {len(all_symbols)} Pacifica markets: {', '.join(all_symbols)}")

        # Step 4: Format market table with all data (candles, RSI, MACD, SMA, etc.)
        market_table = aggregator.format_market_table(market_data)

        # Step 5: If there are open positions, get Deep42 evaluation
        position_evaluations = self._get_position_evaluations(open_positions)

        # Step 8: Get trade history context
        trade_history = ""
        if trade_tracker:
            recent_trades = trade_tracker.get_recent_trades(hours=24, limit=10)
            if recent_trades:
                trade_history = "\n\nRECENT TRADING HISTORY (Last 24h):\n"
                trade_history += "Symbol | Side | Entry Price | Exit Price | P&L | Status | Time\n"
                trade_history += "-" * 80 + "\n"
                for trade in recent_trades[-10:]:  # Show last 10
                    symbol = trade.get('symbol') or 'N/A'
                    side = (trade.get('side') or 'N/A').upper()
                    entry = trade.get('entry_price') or 0
                    exit_price = trade.get('exit_price')
                    pnl = trade.get('pnl') or 0
                    status = trade.get('status') or 'N/A'
                    timestamp = trade.get('timestamp') or ''
                    timestamp_str = timestamp[:16] if timestamp else 'N/A'  # Just date + time
                    
                    # Format exit_price safely
                    if exit_price is None or exit_price == 'N/A':
                        exit_str = 'N/A'
                    else:
                        exit_str = f"${exit_price:.4f}"
                    
                    trade_history += f"{symbol} | {side} | ${entry:.4f} | {exit_str} | ${pnl:.2f} | {status} | {timestamp_str}\n"
        
        # Step 6: Format prompt (include all context - LLM analyzes ALL markets)
        prompt = self.prompt_formatter.format_trading_prompt(
            macro_context=macro_context,
            market_table=market_table,
            open_positions=open_positions,
            deep42_context=deep42_context,
            token_analyses="",  # Not using token-specific analyses - analyzing all markets directly
            hourly_review=hourly_review,  # Hourly deep research review if provided
            position_evaluations=position_evaluations,
            analyzed_tokens=all_symbols,  # Pass ALL symbols - LLM analyzes everything
            trade_history=trade_history,  # Add trade history
            recently_closed_symbols=recently_closed_symbols or [],  # Add recently closed symbols
            account_balance=account_balance  # Add account balance
        )

        # Step 9: Query LLM with retries
        responses = []
        for attempt in range(self.max_retries + 1):
            logger.info(f"LLM query attempt {attempt + 1}/{self.max_retries + 1}...")

            # Query model (increase max_tokens for multiple decisions)
            result = self.model_client.query(
                prompt=prompt,
                max_tokens=500,  # Increased for multiple decisions
                temperature=0.1
            )

            if result is None:
                logger.error(f"LLM query failed (attempt {attempt + 1})")
                continue

            # Add response to list
            responses.append(result["content"])

            # Try parsing multiple decisions
            parsed_decisions = self.response_parser.parse_multiple_decisions(result["content"])
            if parsed_decisions is None or len(parsed_decisions) == 0:
                logger.warning(f"Parse failed (attempt {attempt + 1}), will retry with clearer prompt")

                # Modify prompt for retry (make format requirement clearer)
                if attempt < self.max_retries:
                    prompt += (
                        f"\n\nIMPORTANT: Analyze ALL {len(all_symbols)} markets below and respond with decisions ONLY for markets with clear trading signals:\n"
                        "TOKEN: PUMP\n"
                        "DECISION: BUY PUMP\n"
                        "CONFIDENCE: 0.75\n"
                        "REASON: Your reasoning here\n\n"
                        "TOKEN: SOL\n"
                        "DECISION: SELL SOL\n"
                        "CONFIDENCE: 0.65\n"
                        "REASON: Your reasoning here\n\n"
                        "Do NOT add any other text before or after."
                    )
                continue

            # Validate all decisions (track positions as we go)
            valid_decisions = []
            current_positions = open_positions.copy() if open_positions else []
            
            for parsed in parsed_decisions:
                # Check if symbol was recently closed (prevent immediate re-entry)
                # Only block if it was closed VERY recently (within 30 min) - give more freedom
                if parsed.get("symbol") and recently_closed_symbols:
                    if parsed["symbol"] in recently_closed_symbols and parsed["action"] in ["BUY", "SELL"]:
                        logger.warning(f"⚠️ {parsed['action']} {parsed['symbol']}: Recently closed (within 2h) - but allowing if strong signal")
                        # Don't block - just warn. Let the LLM's confidence decide.
                        # Only block if confidence is low (< 0.7)
                        if parsed.get("confidence", 0.5) < 0.7:
                            logger.warning(f"Skipping {parsed['action']} {parsed['symbol']}: Low confidence on recently closed symbol")
                            continue
                
                is_valid, error = self.response_parser.validate_decision(
                    parsed,
                    current_positions,  # Use current positions (updated as we validate)
                    self.max_positions  # Use max_positions from agent (15)
                )
                
                if is_valid:
                    valid_decisions.append(parsed)
                    # Update current_positions for next validation (simulate opening position)
                    if parsed["action"] in ["BUY", "SELL"]:
                        current_positions.append({"symbol": parsed["symbol"]})
                else:
                    logger.warning(f"Decision validation failed for {parsed.get('symbol', 'UNKNOWN')}: {error}")

            if valid_decisions:
                # Success! Return list of decisions
                logger.info(f"✅ Valid trading decisions: {len(valid_decisions)} decisions")
                
                # Return list of decisions with metadata
                return [
                    {
                        "action": parsed["action"],
                        "symbol": parsed["symbol"],
                        "reason": parsed["reason"],
                        "confidence": parsed.get("confidence", 0.5),
                        "cost": result["cost"] / len(valid_decisions),  # Split cost across decisions
                        "prompt_tokens": result["usage"]["prompt_tokens"],
                        "completion_tokens": result["usage"]["completion_tokens"]
                    }
                    for parsed in valid_decisions
                ]
            else:
                logger.warning(f"All {len(parsed_decisions)} decisions failed validation")

                # If validation failed, retry with updated prompt
                if attempt < self.max_retries:
                    prompt += f"\n\nNote: {error}. Please choose a different action."

        # All retries exhausted - fallback to NOTHING
        logger.error("All LLM query/parse attempts failed, falling back to NOTHING")
        return None  # Return None on failure

    def get_daily_spend(self) -> float:
        """Get current daily spend"""
        return self.model_client.get_daily_spend()

    def get_remaining_budget(self) -> float:
        """Get remaining budget for today"""
        return self.model_client.get_remaining_budget()
