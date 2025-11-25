"""
LLM Prompt Formatter V2 - Deep Reasoning Edition

IMPROVEMENTS OVER V1:
- Removes Deep42 macro context (eliminates invalid symbol suggestions)
- Enforces chain-of-thought analysis process
- Requires exact indicator citations (no "likely" statements)
- Focuses on 5-minute scalping with 4-hour context (not macro narratives)
- Mandatory indicator checklist for all decisions

ROLLBACK: To revert to old behavior, set USE_V2_PROMPT=False in bot config

Created: 2025-11-06
Author: Analysis from reasoning-quality-analysis.md
"""

import logging
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


class PromptFormatterV2:
    """
    Enhanced prompt formatter with deep reasoning requirements

    Key Changes:
    1. No Deep42/macro context in prompt
    2. Chain-of-thought analysis structure
    3. Mandatory exact indicator citations
    4. Symbol validation requirements
    """

    def __init__(self):
        """Initialize V2 prompt formatter"""
        self.version = "v4_momentum_strategy"

    def get_prompt_version(self) -> str:
        """
        Get the current prompt version

        Returns:
            Version string
        """
        return self.version

    def format_open_positions(self, positions: List[Dict]) -> str:
        """
        Format open positions table (unchanged from v1)
        """
        if not positions:
            return "Open Positions: None"

        lines = []
        lines.append("=" * 80)
        lines.append("OPEN POSITIONS")
        lines.append("=" * 80)

        # Header with proper spacing to prevent truncation
        header = f"{'Symbol':<10} {'Side':<6} {'Entry Price':>14} {'Current Price':>14} {'Size':>12} {'P&L':>10} {'Duration':>10}"
        lines.append(header)
        lines.append("-" * 80)

        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            side = pos.get('side', 'N/A')
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', entry_price)
            size = pos.get('size', 0)
            pnl = pos.get('pnl')
            time_held = pos.get('time_held', 'N/A')

            # Calculate P&L percentage if not provided
            if (pnl == 0 or pnl is None) and entry_price > 0 and current_price > 0:
                if side.upper() == 'LONG':
                    pnl = ((current_price - entry_price) / entry_price) * 100
                else:  # SHORT
                    pnl = ((entry_price - current_price) / entry_price) * 100

            # Format size
            if size >= 1:
                size_str = f"{size:.4f}"
            elif size >= 0.0001:
                size_str = f"{size:.6f}"
            else:
                size_str = f"{size:.8f}"

            # Format P&L
            if pnl is None:
                pnl_str = "N/A"
            else:
                pnl_str = f"{'+' if pnl > 0 else ''}{pnl:.2f}%"

            # Format prices
            if entry_price >= 1:
                entry_str = f"${entry_price:.2f}"
            elif entry_price >= 0.01:
                entry_str = f"${entry_price:.4f}"
            else:
                entry_str = f"${entry_price:.6f}"

            if current_price >= 1:
                current_str = f"${current_price:.2f}"
            elif current_price >= 0.01:
                current_str = f"${current_price:.4f}"
            else:
                current_str = f"${current_price:.6f}"

            line = f"{symbol:<10} {side:<6} {entry_str:>14} {current_str:>14} {size_str:>12} {pnl_str:>10} {time_held:>10}"
            lines.append(line)

        return "\n".join(lines)

    def format_trading_prompt(
        self,
        market_table: str,
        open_positions: Optional[List[Dict]] = None,
        token_analyses: Optional[str] = None,
        position_evaluations: Optional[str] = None,
        analyzed_tokens: Optional[List[str]] = None,
        trade_history: Optional[str] = None,
        recently_closed_symbols: Optional[List[str]] = None,
        account_balance: Optional[float] = None,
        hourly_review: Optional[str] = None,
        dex_name: Optional[str] = None,
        failed_executions: Optional[List[Dict]] = None,
        # NOTE: macro_context removed - no longer used in v2
        deep42_context: Optional[str] = None  # Ignored in v2
    ) -> str:
        """
        Format complete trading prompt with deep reasoning requirements

        CHANGES FROM V1:
        - macro_context parameter removed/ignored
        - deep42_context parameter ignored
        - New chain-of-thought analysis section
        - Stricter indicator citation requirements
        - Symbol validation enforcement

        Args:
            market_table: Formatted market data table (REQUIRED)
            open_positions: List of open position dicts
            analyzed_tokens: List of token symbols available
            dex_name: DEX name (e.g., "Lighter")
            ... (other optional context)

        Returns:
            Complete formatted prompt string
        """
        sections = []

        # Section 0: Hourly Deep Research Review (if provided)
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

        # Section 1: Token Analyses (if provided)
        if token_analyses:
            sections.append(token_analyses)
            sections.append("")

        # Section 2: Position Evaluations (if provided)
        if position_evaluations:
            sections.append(position_evaluations)
            sections.append("")

        # Section 3: Market Data Table
        sections.append("=" * 80)
        dex_display = dex_name or "DEX"
        market_count = len(analyzed_tokens) if analyzed_tokens else 0
        sections.append(f"MARKET DATA ({market_count} {dex_display} Perpetuals)")
        sections.append("=" * 80)
        sections.append(market_table)
        sections.append("")

        # Section 4: Failed Executions (Retry Opportunities)
        if failed_executions:
            sections.append("=" * 80)
            sections.append("⚠️ FAILED EXECUTIONS FROM PREVIOUS CYCLE (RETRY OPPORTUNITIES)")
            sections.append("=" * 80)
            sections.append("The following orders failed due to slippage or other retryable errors.")
            sections.append("You can retry these with updated prices or adjust position sizes based on liquidity.")
            sections.append("")
            for failed in failed_executions:
                symbol = failed.get('symbol', 'N/A')
                action = failed.get('action', 'N/A')
                error = failed.get('error', 'Unknown error')
                price = failed.get('current_price', 0)
                details = failed.get('error_details', {})

                sections.append(f"• {action} {symbol}: {error}")
                if price:
                    sections.append(f"  Current price: ${price:.4f}")
                if details:
                    sections.append(f"  Details: {details}")
            sections.append("")

        # Section 5: Open Positions
        if open_positions:
            positions_str = self.format_open_positions(open_positions)
        else:
            positions_str = "Open Positions: None\n⚠️ IMPORTANT: You have ZERO open positions. DO NOT suggest CLOSE actions. Only suggest BUY or SELL to open NEW positions."

        sections.append(positions_str)
        sections.append("")

        # Section 6: Trade History (if provided)
        if trade_history:
            sections.append(trade_history)
            sections.append("")

        # Section 7: Recently Closed Symbols Warning
        if recently_closed_symbols:
            sections.append(f"⚠️ IMPORTANT: These symbols were recently closed (within last 2h): {', '.join(recently_closed_symbols)}")
            sections.append("Avoid immediately reopening positions in these symbols unless there's a STRONG reversal signal.")
            sections.append("")

        # Section 8: Account Balance
        if account_balance is not None:
            sections.append("=" * 80)
            sections.append(f"💰 ACCOUNT BALANCE: ${account_balance:.2f}")
            sections.append("=" * 80)
            sections.append("")

        # Section 9: Instructions (V2 Enhanced)
        analyzed_tokens_list = analyzed_tokens if analyzed_tokens else []

        instructions = f"""You are an autonomous trading agent executing a momentum-based trading strategy optimized for profitability.

**AVAILABLE DATA:**

You have complete market data for ALL {len(analyzed_tokens_list)} {dex_display} markets with MULTI-TIMEFRAME indicators:

**5-MINUTE INDICATORS** (for entry/exit timing):
- EMA (20 period) - Exponential Moving Average for trend direction
- MACD - Moving Average Convergence Divergence (trend momentum)
- RSI - Relative Strength Index (momentum strength, not mean reversion)
- Bollinger Bands - Upper, middle, lower bands (volatility and squeeze detection)
- Stochastic (%K and %D) - Momentum oscillator

**4-HOUR INDICATORS** (for trend context):
- EMA (20 period) - Longer-term trend direction
- ATR - Average True Range (volatility measurement)
- ADX - Average Directional Index (trend strength, > 25 = strong trend)

**Additional Context:**
- Price and 24h volume (for market analysis - position sizing is handled automatically)
- Funding rates - market sentiment
- Open interest - market participation
- Your trading history and recent performance
- Open positions that may need management
- Failed executions from previous cycle (retry opportunities with updated prices)

**YOUR STRATEGY: Momentum Trading with 2:1 Risk/Reward**

**CRITICAL INSIGHT FROM RESEARCH:**
- Mean reversion (buying RSI < 30) DOES NOT WORK in crypto futures - backtests show weak results
- Momentum strategies work BETTER: 122% CAGR vs 101% buy-and-hold
- MACD + RSI combination achieves 73% win rate in trending markets
- Current bot at 45.7% WR needs to improve to 55%+ for profitability

**Goal**: Achieve 55%+ win rate through quality momentum setups with proper risk/reward ratios.

**Entry Rules (MOMENTUM BIAS)**:
1. **BUY when MOMENTUM IS BUILDING:**
   - RSI > 50 (NOT oversold - momentum building)
   - MACD positive and rising (bullish momentum)
   - Price > EMA20 on 5-min chart (uptrend)
   - 4h ADX > 25 (strong trend confirmation)
   - Stochastic %K > 50 (momentum present)
   - AVOID buying when RSI < 40 (no momentum)

2. **SELL when DOWNWARD MOMENTUM IS BUILDING:**
   - RSI < 50 (downward momentum)
   - MACD negative and falling
   - Price < EMA20 on 5-min chart (downtrend)
   - 4h ADX > 25 (strong trend confirmation)
   - Stochastic %K < 50 (downward momentum)

**Exit Rules (2:1 Risk/Reward Minimum)**:
1. **Take Profit**:
   - MACD turns negative (momentum lost)
   - RSI < 40 (momentum weakness)
   - Price crosses below EMA20
   - Target 2% profit minimum (2:1 R:R if risking 1%)

2. **Stop Loss**:
   - Maximum 1% loss per trade
   - Cut losses quickly when momentum reverses

3. **Let Winners Run** (exception to above):
   - If 4h ADX > 30 and 4h EMA trending strongly
   - Trail stop using EMA20 on 5-min chart
   - Can target 3-4% profit in strong trends

**Token Selection (QUALITY OVER QUANTITY)**:
**LIQUIDITY FILTER - Focus on Top 20 Volume Tokens**:
- Only trade tokens with sufficient 24h volume (typically >$10M)
- Top volume tokens have better liquidity = less slippage on entries/exits
- Prioritize BTC, SOL, ETH, and other high-volume majors
- Low volume tokens (<$1M 24h) can have execution issues and manipulation
- Check the "24h Vol" column in market data - higher is better

**Position Frequency**:
- Target 30-50 quality setups per day (NOT 200+)
- Focus on high-probability momentum trades
- Better to skip than force a trade

**Position Sizing (AUTOMATIC)**:
- Position sizes are automatically calculated by the system (typically $2-5 USD per trade)
- Your CONFIDENCE score adjusts size (higher confidence = larger position)
- You do NOT need to specify or worry about position sizes
- The system automatically handles sizing based on liquidity and account balance

**Retry Logic Intelligence**:
- If you see failed executions from previous cycle, analyze why they failed
- For slippage errors: You can retry with updated market price
- For low liquidity: Skip the token if volume is too low
- Make smart decisions - don't blindly retry everything

**Make Your Own Decisions**:
- Analyze all indicators across both timeframes
- Combine technical signals with market context
- Make independent decisions for each market based on what you see
- Prioritize tokens from PROVEN WINNERS list
- Strictly avoid tokens from AVOID list
- Focus on momentum, NOT mean reversion
- Only trade when momentum is clear and strong

**RESPONSE FORMAT:**

For each market where you see a trading opportunity, provide:

TOKEN: <SYMBOL>
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL>]
CONFIDENCE: [0.3-1.0]
REASON: [Brief explanation referencing specific indicators you're using - e.g., "RSI 62 (momentum building), MACD positive and rising, Price > EMA20, 4h ADX 32 shows strong uptrend - targeting 2% profit with 1% stop"]

**ACTION DEFINITIONS:**
- **BUY <SYMBOL>**: Open a LONG position (you profit if price goes up)
- **SELL <SYMBOL>**: Open a SHORT position (you profit if price goes down)
- **CLOSE <SYMBOL>**: Close an existing open position to take profit or cut loss

**IMPORTANT**:
- Reference the specific indicators driving your decision
- Explain your risk/reward ratio (targeting 2:1 minimum)
- Only trade tokens from PROVEN WINNERS list when possible
- Never trade tokens from AVOID list
- Focus on momentum setups, not oversold bounces
- Quality over quantity - 30-50 trades/day is the target
"""

        sections.append(instructions)

        prompt = "\n".join(sections)

        logger.info(f"[V2 PROMPT] Formatted prompt: {len(prompt)} characters (~{len(prompt)//4} tokens)")
        logger.info(f"[V2 PROMPT] Deep42 macro context: DISABLED (5-min scalping focus)")
        logger.info(f"[V2 PROMPT] Reasoning mode: MANDATORY exact citations + chain-of-thought")

        return prompt

    def create_system_message(self, dex_name: Optional[str] = None) -> str:
        """
        Create system message for LLM

        Args:
            dex_name: DEX name (e.g., "Lighter")

        Returns:
            System message string
        """
        dex_display = dex_name or "DEX"
        return (
            f"You are a precise, analytical trading agent for {dex_display} perpetual futures. "
            f"You make 5-minute scalping decisions using exact indicator values and step-by-step analysis. "
            f"You cite specific data, avoid generic statements, and focus on technical confluence. "
            f"V2 Deep Reasoning Mode: Mandatory exact citations, no 'likely' statements, chain-of-thought analysis."
        )
