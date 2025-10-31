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
        position_evaluations: Optional[str] = None
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

        # Instructions
        instructions = """Instructions:
- Consider the macro context (overall market state, catalysts, outlook)
- Analyze current market data (price, volume, funding, OI, indicators)
- Review open positions (if any) and decide if you should CLOSE them or let them run
- Make ONE decision: BUY <SYMBOL>, SELL <SYMBOL>, CLOSE <SYMBOL>, or NOTHING
- Explain your reasoning citing SPECIFIC data sources (e.g., "Deep42 analysis shows...", "Fear & Greed index at X...", "SOL RSI at Y...", "Funding rate at Z...")

Decision Options:
- BUY <SYMBOL>: Enter new long position (only if room for more positions)
- SELL <SYMBOL>: Enter new short position (only if room for more positions)
- CLOSE <SYMBOL>: Close existing position (if it's time to exit based on your analysis)
- NOTHING: No action (ONLY if market is extremely uncertain - prefer action over inaction)

You have FULL FREEDOM to:
- Choose ANY symbol from the 28 available markets
- Decide when to enter and exit positions based on your analysis
- Set your own profit targets and risk tolerance
- Hold positions as long or short as you think optimal
- React to changing macro conditions and market data

SWING TRADING STRATEGY (Daily/Weekly Timeframes):
- Focus on DAILY and WEEKLY price movements, not long-term trends
- Look for 24h volume spikes (>50% increase = strong signal)
- When Fear & Greed < 30: Look for contrarian LONG entries on oversold tokens (RSI < 40)
- When Fear & Greed > 70: Consider taking profits or SHORT entries on overbought tokens (RSI > 70)
- Don't wait for perfect setups - edge comes from acting when others hesitate
- Short-term volatility is opportunity, not risk
- Small losses are acceptable - the goal is profitable trades, not just capital preservation

POSITION MANAGEMENT (CRITICAL):
- **Fee consideration**: Each trade costs $0.02 in fees ($30 position = 0.067%). You need AT LEAST 0.5-1% profit to overcome fees and make meaningful gains.
- **When to CLOSE a position**:
  * ✅ **Profit target hit**: +1.5% to +3% - CLOSE IMMEDIATELY when target reached (regardless of time held)
  * ✅ **Stop loss hit**: -1% to -1.5% - CLOSE IMMEDIATELY to cut losses
  * ✅ **Clear reversal signal**: Trend changed, RSI reversed from overbought/oversold, volume dried up
  * ✅ **Better opportunity**: New setup with stronger signal than current position
  * ❌ **DO NOT close** just because: Position is "flat" or "small profit" after a few minutes - swing trades need time to develop
  * ❌ **DO NOT close** prematurely: If position is moving in right direction but hasn't hit target yet, let it run
- **Think in terms of swing moves**: Swing trades develop over hours/days. If you hit profit target in 5 minutes, take it! But don't close just because position hasn't moved much after 5 minutes.

Respond in this EXACT format:
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL> | NOTHING]
REASON: [Your reasoning citing macro + market data in 2-3 sentences]"""

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
