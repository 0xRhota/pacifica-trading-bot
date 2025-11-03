"""
LLM Prompt Formatter
Formats market data into 3-section prompts for trading decisions

Section 1: Macro Context (cached 12h)
Section 2: Market Data Table (all 28 markets, fresh)
Section 3: Open Positions (if any)

Usage:
    formatter = PromptFormatter()
    prompt = formatter.format_trading_prompt(
        macro_context="...",
        market_table="...",
        open_positions=[]
    )
"""

import logging
import os
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class PromptFormatter:
    """Format market data for LLM prompts"""

    def __init__(self):
        """Initialize prompt formatter"""
        self._current_version = None

    def get_prompt_version(self) -> str:
        """
        Detect which prompt version is currently active by comparing
        instructions with archive files
        
        Returns:
            Version name (e.g., "v3_longer_holds") or "unknown"
        """
        if self._current_version:
            return self._current_version
        
        try:
            # Get current instructions
            current_instructions = self._get_current_instructions()
            if not current_instructions:
                return "unknown"
            
            # Check archive files
            archive_dir = "llm_agent/prompts_archive"
            if not os.path.exists(archive_dir):
                return "unknown"
            
            # Compare with each archive file
            for filename in os.listdir(archive_dir):
                if filename.endswith('.txt'):
                    version_name = filename[:-4]  # Remove .txt
                    archive_path = os.path.join(archive_dir, filename)
                    
                    with open(archive_path, 'r') as f:
                        archive_content = f.read().strip()
                    
                    # Compare (normalize whitespace)
                    if self._normalize_text(current_instructions) == self._normalize_text(archive_content):
                        self._current_version = version_name
                        return version_name
            
            # If no match found, return "unknown"
            return "unknown"
            
        except Exception as e:
            logger.warning(f"Failed to detect prompt version: {e}")
            return "unknown"
    
    def _get_current_instructions(self) -> Optional[str]:
        """Extract current instructions from prompt_formatter.py"""
        try:
            prompt_file = "llm_agent/llm/prompt_formatter.py"
            with open(prompt_file, 'r') as f:
                content = f.read()
            
            # Extract instructions between '# Instructions' and closing '"""'
            import re
            pattern = r'(        # Instructions\n        instructions = """).*?(""")'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                full_match = match.group(0)
                # Extract just the content between the triple quotes
                instructions = full_match.split('"""')[1].strip()
                return instructions
            return None
        except Exception as e:
            logger.warning(f"Failed to extract instructions: {e}")
            return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (remove extra whitespace)"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)

    def format_open_positions(self, positions: List[Dict]) -> str:
        """
        Format open positions for LLM prompt

        Args:
            positions: List of position dicts with keys:
                - symbol: str
                - side: str (LONG/SHORT)
                - entry_price: float
                - current_price: float
                - size: float
                - pnl: float
                - time_held: str

        Returns:
            Formatted positions string
        """
        if not positions:
            return "Open Positions: None"

        lines = ["Open Positions:"]
        lines.append(
            f"{'Symbol':<10} {'Side':<6} {'Entry':>12} {'Current':>12} "
            f"{'Size':>10} {'P&L':>10} {'Time':>10}"
        )
        lines.append("-" * 80)

        for pos in positions:
            symbol = pos.get('symbol', 'UNKNOWN')
            side = pos.get('side', 'UNKNOWN')
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', 0)
            size = pos.get('size', 0)
            pnl = pos.get('pnl', 0)
            time_held = pos.get('time_held', 'N/A')

            # Format size
            if size >= 1:
                size_str = f"{size:.4f}"
            else:
                size_str = f"{size:.6f}"

            # Format P&L
            if pnl is None:
                pnl_str = "N/A"
            else:
                pnl_str = f"{'+' if pnl > 0 else ''}{pnl:.2f}%"

            lines.append(
                f"{symbol:<10} {side:<6} ${entry_price:>11.2f} ${current_price:>11.2f} "
                f"{size_str:>10} {pnl_str:>10} {time_held:>10}"
            )

        return "\n".join(lines)

    def format_trading_prompt(
        self,
        macro_context: str,
        market_table: str,
        open_positions: Optional[List[Dict]] = None,
        deep42_context: Optional[str] = None,
        token_analyses: Optional[str] = None,
        position_evaluations: Optional[str] = None,
        analyzed_tokens: Optional[List[str]] = None,
        trade_history: Optional[str] = None,
        recently_closed_symbols: Optional[List[str]] = None,
        account_balance: Optional[float] = None,
        hourly_review: Optional[str] = None  # Hourly deep research review
    ) -> str:
        """
        Format complete trading prompt for LLM

        Args:
            macro_context: Formatted macro context string
            market_table: Formatted market data table
            open_positions: List of open position dicts (optional)
            deep42_context: Custom Deep42 context (optional)
            token_analyses: Token analysis results (optional)
            position_evaluations: Position evaluation results (optional)

        Returns:
            Complete formatted prompt string
        """
        sections = []

        # Section 0: Hourly Deep Research Review (if provided - appears FIRST for emphasis)
        if hourly_review:
            sections.append(hourly_review)
            sections.append("")
            sections.append("⚠️ **THIS IS YOUR HOURLY DEEP RESEARCH CYCLE**")
            sections.append("")
            sections.append("The data above shows YOUR decisions and their outcomes from the past hour.")
            sections.append("You MUST use sequential thinking to analyze WHY decisions were made,")
            sections.append("how they turned out, and what patterns you can learn from.")
            sections.append("")
            sections.append("Apply the insights from your analysis to make better decisions in this cycle.")
            sections.append("")

        # Section 1: Custom Deep42 Context (if provided)
        if deep42_context:
            sections.append(deep42_context)
            sections.append("")

        # Section 2: Token Analyses (if provided)
        if token_analyses:
            sections.append(token_analyses)
            sections.append("")

        # Section 3: Position Evaluations (if provided)
        if position_evaluations:
            sections.append(position_evaluations)
            sections.append("")

        # Section 4: Macro Context
        sections.append(macro_context)
        sections.append("")

        # Section 5: Market Data Table
        sections.append("=" * 80)
        sections.append("MARKET DATA (28 Pacifica Perpetuals)")
        sections.append("=" * 80)
        sections.append(market_table)
        sections.append("")

        # Section 6: Open Positions
        if open_positions:
            positions_str = self.format_open_positions(open_positions)
        else:
            positions_str = "Open Positions: None"

        sections.append(positions_str)
        sections.append("")
        
        # Section 7: Trade History (if provided)
        if trade_history:
            sections.append(trade_history)
            sections.append("")
        
        # Section 8: Recently Closed Symbols Warning (if provided)
        if recently_closed_symbols:
            sections.append(f"⚠️ IMPORTANT: These symbols were recently closed (within last 2h): {', '.join(recently_closed_symbols)}")
            sections.append("Avoid immediately reopening positions in these symbols unless there's a STRONG reversal signal.")
            sections.append("")

        # Section 9: Account Balance (if provided)
        if account_balance is not None:
            sections.append("=" * 80)
            sections.append(f"💰 ACCOUNT BALANCE: ${account_balance:.2f}")
            sections.append("=" * 80)
            sections.append("")

        # Instructions
        analyzed_tokens_list = analyzed_tokens if analyzed_tokens else []
        analyzed_tokens_str = ", ".join(analyzed_tokens_list) if analyzed_tokens_list else "N/A"
        
        instructions = f"""You are an autonomous trading agent analyzing cryptocurrency markets.

**AVAILABLE DATA:**

You have complete market data for ALL {len(analyzed_tokens_list)} Pacifica markets:

1. **Market Data Table** (shown below) - Complete technical indicators for every market:
   - Price and 24h volume
   - RSI (Relative Strength Index) - momentum/overbought/oversold levels
   - MACD (Moving Average Convergence Divergence) - trend direction and crossovers  
   - SMA 20 vs SMA 50 - short-term vs long-term trend comparison
   - Funding rates - market sentiment (positive = bullish, negative = bearish)
   - Open interest - market participation levels
   - Full OHLCV candle data for technical analysis

2. **Macro Context** - Overall market conditions (Fear & Greed, BTC dominance, funding rates, Deep42 analysis)

3. **Your Trading History** - Recent trades and performance (learn from wins/losses)

4. **Open Positions** - Current positions that may need management

5. **Account Balance** - Available capital for new positions (you can open up to 15 positions)

6. **Proven Strategy Patterns** - Backtested strategies that have shown profitability:
   - **MomentumSqueeze Pattern** (1.06% return, 1.48 Sharpe, -1.13% max drawdown):
     * Bollinger Band squeeze (bands tighten - low volatility before breakout)
     * OBV (On-Balance Volume) crosses above its EMA (accumulation signal)
     * Price breaks above upper Bollinger Band (momentum breakout)
     * Exit when OBV crosses below EMA (distribution signal)
   - Use these patterns as reference when you see similar setups - they're proven to work

**YOUR TASK:**

Review ALL {len(analyzed_tokens_list)} markets in the data table below. For each market, examine the data:
- Technical indicators (RSI, MACD, SMA, volume, price action)
- Market sentiment (funding rates, open interest)
- Relative strength compared to other markets
- Your trading history (what's worked, what hasn't)

Then make independent trading decisions based purely on what you see in the data:
- BUY (long) if you identify a strong bullish opportunity
- SELL (short) if you identify a strong bearish opportunity  
- CLOSE if you have an open position that should be closed
- NOTHING if no clear opportunity exists

**NO CONSTRAINTS:**
- Trade any market that shows opportunity
- Make as many or as few decisions as you want (based on what you see)
- Use any timeframe or strategy that makes sense
- Size positions based on your confidence and available balance
- Trust your analysis of the data

**RESPONSE FORMAT:**

For each market where you see a trading opportunity, provide:

TOKEN: <SYMBOL>
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL>]
CONFIDENCE: [0.3-1.0]
REASON: [Brief explanation of what you see in the data that supports this decision]

You don't need to respond for every market - only respond for markets where you see a clear opportunity based on the data.

Example responses:

TOKEN: PUMP
DECISION: BUY PUMP
CONFIDENCE: 0.75
REASON: RSI 35 indicates oversold, MACD showing bullish crossover, volume up 45%, positive funding rate suggests long bias. Strong technical setup.

TOKEN: SOL
DECISION: SELL SOL
CONFIDENCE: 0.68
REASON: RSI 72 is overbought, SMA20 below SMA50 shows downtrend, negative funding rate indicates bearish sentiment. Price rejection at resistance.

TOKEN: DOGE
DECISION: CLOSE DOGE
CONFIDENCE: 0.80
REASON: Open long position has hit target, RSI now neutral, taking profit before potential reversal. Locking in gains.

"""

        sections.append(instructions)

        prompt = "\n".join(sections)

        logger.info(f"Formatted prompt: {len(prompt)} characters (~{len(prompt)//4} tokens)")
        return prompt

    def create_system_message(self) -> str:
        """
        Create system message for LLM (optional, for context setting)

        Returns:
            System message string
        """
        return (
            "You are a trading agent for Pacifica DEX perpetual futures. "
            "Analyze macro market context, current market data, and open positions. "
            "Make trading decisions based on your analysis."
        )
