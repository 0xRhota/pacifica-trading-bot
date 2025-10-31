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
from .prompt_formatter import PromptFormatter
from .response_parser import ResponseParser
from .deep42_tool import Deep42Tool
from .token_analysis_tool import TokenAnalysisTool

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
        max_positions: int = 3
    ):
        """
        Initialize LLM trading agent

        Args:
            deepseek_api_key: DeepSeek API key
            cambrian_api_key: Cambrian API key for Deep42 queries
            model: Model name (default: deepseek-chat)
            max_retries: Number of retries on parse failure (default: 2)
            daily_spend_limit: Max USD to spend per day (default: $10)
            max_positions: Max open positions allowed (default: 3)
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

        self.prompt_formatter = PromptFormatter()
        self.response_parser = ResponseParser()

        # Initialize Deep42 tool for custom LLM queries
        self.deep42_tool = Deep42Tool(cambrian_api_key=cambrian_api_key)

        # Initialize token analysis tool for dynamic token discovery
        self.token_tool = TokenAnalysisTool(cambrian_api_key=cambrian_api_key)

        # Track recent queries to avoid repetition (keep last 5)
        self.recent_queries = []

        logger.info(f"✅ LLMTradingAgent initialized (model={model}, max_positions={max_positions})")

    def _generate_deep42_query(self) -> Optional[str]:
        """
        Ask LLM to generate a custom Deep42 query for daily/weekly context

        Returns:
            Custom question string to ask Deep42, or None if failed
        """
        from datetime import datetime

        today = datetime.now().strftime("%A, %B %d, %Y")

        # Build recent query context to avoid repetition
        avoid_section = ""
        if self.recent_queries:
            avoid_section = f"\n\nDO NOT ASK SIMILAR QUESTIONS TO THESE RECENT ONES:\n"
            for i, q in enumerate(self.recent_queries[-5:], 1):
                avoid_section += f"{i}. {q}\n"
            avoid_section += "\nGenerate a COMPLETELY DIFFERENT question type.\n"

        query_generation_prompt = f"""You are a crypto trading bot about to make trading decisions on Solana DEX markets.

Today's date: {today}

Your task: Generate a single, focused question to ask Deep42 (a crypto market intelligence API) that will give you the most useful daily or weekly context for making trading decisions RIGHT NOW.

Guidelines:
- Focus on TODAY or THIS WEEK's events, catalysts, news, or token-specific developments
- Be specific about tokens, protocols, or market segments if relevant
- Ask about actionable information (launches, updates, sentiment shifts, breaking news)
- Avoid generic questions everyone already knows (e.g., "alt season potential")

Examples of GOOD questions (ASK DIFFERENT TYPES EACH TIME):
- "What are whale wallets accumulating right now based on on-chain data?"
- "Are there major unlock events or vesting schedules ending this week for any top 100 tokens?"
- "What tokens have unusual social sentiment spikes or FUD campaigns in the last 12 hours?"
- "Are there any imminent protocol upgrades, governance votes, or treasury decisions for DeFi blue chips?"
- "What narratives are gaining momentum on crypto Twitter in the last 24 hours?"
- "Are there any regulatory news, exchange listings, or institutional moves announced today?"
- "Which Solana meme coins have suspicious volume patterns or rug pull risks today?"
- "What major partnerships or integrations were announced this week in the Solana ecosystem?"
- "Are there any major DEX or lending protocol exploits or security incidents reported today?"
- "Which tokens have the highest funding rates right now and what does that signal?"
{avoid_section}
VARY YOUR QUESTION - mix on-chain data, social sentiment, events, narratives, risk analysis, technical analysis, macro factors, etc.

Respond with ONLY the question, no other text."""

        try:
            result = self.model_client.query(
                prompt=query_generation_prompt,
                max_tokens=150,
                temperature=0.8  # Higher temp for more variety
            )

            if result is None:
                logger.warning("Failed to generate Deep42 query from LLM")
                return None

            question = result["content"].strip()
            logger.info(f"Generated Deep42 query: {question}")

            # Track this query to avoid repeating it
            self.recent_queries.append(question)
            if len(self.recent_queries) > 5:
                self.recent_queries.pop(0)  # Keep only last 5

            return question

        except Exception as e:
            logger.error(f"Error generating Deep42 query: {e}")
            return None

    def _get_deep42_context(self) -> str:
        """
        Get custom Deep42 context by having LLM generate query and execute it

        Returns:
            Deep42's answer formatted for inclusion in trading prompt
        """
        logger.info("Getting custom Deep42 context...")

        # Step 1: LLM generates custom query
        question = self._generate_deep42_query()

        if question is None:
            return "⚠️ Deep42 query generation failed"

        # Step 2: Execute query against Deep42
        answer = self.deep42_tool.query(question)

        if answer is None:
            return f"⚠️ Deep42 query failed\nQuestion asked: {question}"

        # Step 3: Format for prompt
        return f"""Custom Deep42 Query (Daily/Weekly Context):
Question: {question}

Deep42 Answer (Cambrian Network):
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
        from datetime import datetime

        today = datetime.now().strftime("%A, %B %d, %Y")

        # Sample tokens for prompt (show top 50)
        token_list = ", ".join(available_tokens[:50])

        selection_prompt = f"""You are a crypto trading bot analyzing markets to make trading decisions.

Today's date: {today}

Available perpetual tokens (sorted by open interest):
{token_list}

Your task: Select {num_tokens} tokens that you want to analyze in depth before making your trading decision.

Guidelines:
- Consider tokens with interesting price action, recent news, or catalysts
- Mix major assets (BTC, ETH, SOL) with altcoins if relevant
- Think about what's trending or has volatility potential
- Avoid tokens you have no context about

Respond with ONLY the {num_tokens} token symbols separated by commas, no other text.
Example: BTC, PENGU, HYPE"""

        try:
            result = self.model_client.query(
                prompt=selection_prompt,
                max_tokens=50,
                temperature=0.4  # Slightly creative for token selection
            )

            if result is None:
                logger.warning("Failed to get token selection from LLM")
                return available_tokens[:num_tokens]  # Default to top tokens

            # Parse response (expect: "BTC, ETH, SOL")
            response = result["content"].strip()
            selected = [s.strip() for s in response.split(",")]
            selected = [s for s in selected if s]  # Remove empty strings

            logger.info(f"LLM selected tokens: {selected}")
            return selected[:num_tokens]

        except Exception as e:
            logger.error(f"Error selecting tokens: {e}")
            return available_tokens[:num_tokens]

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
        force_macro_refresh: bool = False
    ) -> Optional[Dict]:
        """
        Get trading decision from LLM

        Args:
            aggregator: MarketDataAggregator instance with fetched data
            open_positions: Current open positions (default: [])
            force_macro_refresh: Force refresh macro context (default: False)

        Returns:
            Dict with keys: action, symbol, reason, cost
            None if decision failed
        """
        if open_positions is None:
            open_positions = []

        logger.info(f"Getting trading decision (open positions: {len(open_positions)})...")

        # Step 1: Get custom Deep42 context (LLM generates query, then executes it)
        deep42_context = self._get_deep42_context()

        # Step 2: Get available tokens and let LLM select which to analyze
        logger.info("Getting available tokens from HyperLiquid...")
        available_tokens = self.token_tool.get_available_tokens(limit=50)

        logger.info("LLM selecting tokens to analyze...")
        selected_tokens = self._select_tokens_to_analyze(available_tokens, num_tokens=3)

        # Step 3: Get Deep42 analysis for selected tokens
        token_analyses = self._get_token_analyses(selected_tokens)

        # Step 4: If there are open positions, get Deep42 evaluation
        position_evaluations = self._get_position_evaluations(open_positions)

        # Step 5: Get macro context (cached or fresh)
        logger.info("Fetching macro context...")
        macro_context = aggregator.get_macro_context(force_refresh=force_macro_refresh)

        # Step 6: Fetch market data for all symbols
        logger.info("Fetching market data for all 28 markets...")
        market_data = aggregator.fetch_all_markets()

        # Step 7: Format market table
        market_table = aggregator.format_market_table(market_data)

        # Step 8: Format prompt (include all context)
        prompt = self.prompt_formatter.format_trading_prompt(
            macro_context=macro_context,
            market_table=market_table,
            open_positions=open_positions,
            deep42_context=deep42_context,
            token_analyses=token_analyses,
            position_evaluations=position_evaluations
        )

        # Step 5: Query LLM with retries
        responses = []
        for attempt in range(self.max_retries + 1):
            logger.info(f"LLM query attempt {attempt + 1}/{self.max_retries + 1}...")

            # Query model
            result = self.model_client.query(
                prompt=prompt,
                max_tokens=100,
                temperature=0.1
            )

            if result is None:
                logger.error(f"LLM query failed (attempt {attempt + 1})")
                continue

            # Add response to list
            responses.append(result["content"])

            # Try parsing
            parsed = self.response_parser.parse_response(result["content"])
            if parsed is None:
                logger.warning(f"Parse failed (attempt {attempt + 1}), will retry with clearer prompt")

                # Modify prompt for retry (make format requirement clearer)
                if attempt < self.max_retries:
                    prompt += (
                        "\n\nIMPORTANT: You MUST respond in this EXACT format:\n"
                        "DECISION: BUY SOL\n"
                        "REASON: Your reasoning here\n\n"
                        "Do NOT add any other text before or after."
                    )
                continue

            # Validate decision
            is_valid, error = self.response_parser.validate_decision(
                parsed,
                open_positions,
                self.max_positions
            )

            if is_valid:
                # Success!
                logger.info(f"✅ Valid trading decision: {parsed['action']} {parsed['symbol'] or ''}")

                return {
                    "action": parsed["action"],
                    "symbol": parsed["symbol"],
                    "reason": parsed["reason"],
                    "cost": result["cost"],
                    "prompt_tokens": result["usage"]["prompt_tokens"],
                    "completion_tokens": result["usage"]["completion_tokens"]
                }
            else:
                logger.warning(f"Decision validation failed: {error}")

                # If validation failed, retry with updated prompt
                if attempt < self.max_retries:
                    prompt += f"\n\nNote: {error}. Please choose a different action."

        # All retries exhausted - fallback to NOTHING
        logger.error("All LLM query/parse attempts failed, falling back to NOTHING")

        return {
            "action": "NOTHING",
            "symbol": None,
            "reason": "LLM failed to provide valid decision after retries",
            "cost": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }

    def get_daily_spend(self) -> float:
        """Get current daily spend"""
        return self.model_client.get_daily_spend()

    def get_remaining_budget(self) -> float:
        """Get remaining budget for today"""
        return self.model_client.get_remaining_budget()
