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

    def __init__(self, strategy_file: str = None):
        """
        Initialize prompt formatter

        Args:
            strategy_file: Path to strategy prompt file (overrides default DEX guidance)
        """
        # V1 Original with Deep42 - Neutral adaptive strategy (2025-11-18)
        self._current_version = "v1_original"
        self._strategy_content = None

        # Load strategy from file if specified
        if strategy_file and os.path.exists(strategy_file):
            try:
                with open(strategy_file, 'r') as f:
                    self._strategy_content = f.read()
                self._current_version = os.path.basename(strategy_file).replace('.txt', '')
                logger.info(f"✅ Loaded strategy from {strategy_file}")
            except Exception as e:
                logger.warning(f"Failed to load strategy file {strategy_file}: {e}")

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
        market_table: str,
        macro_context: Optional[str] = None,
        open_positions: Optional[List[Dict]] = None,
        deep42_context: Optional[str] = None,
        token_analyses: Optional[str] = None,
        position_evaluations: Optional[str] = None,
        analyzed_tokens: Optional[List[str]] = None,
        trade_history: Optional[str] = None,
        recently_closed_symbols: Optional[List[str]] = None,
        account_balance: Optional[float] = None,
        hourly_review: Optional[str] = None,  # Hourly deep research review
        dex_name: Optional[str] = None  # DEX name for platform-specific guidance
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
            # Handle both string and dict formats
            if isinstance(deep42_context, dict):
                # Format multi-timeframe Deep42 context
                deep42_str = "=" * 80 + "\n"
                deep42_str += "DEEP42 MULTI-TIMEFRAME ANALYSIS\n"
                deep42_str += "=" * 80 + "\n\n"

                if "regime" in deep42_context:
                    deep42_str += "📊 MARKET REGIME (Updated Hourly):\n"
                    deep42_str += deep42_context["regime"] + "\n\n"

                if "btc_health" in deep42_context:
                    deep42_str += "₿ BTC HEALTH INDICATOR (Updated Every 4h):\n"
                    deep42_str += deep42_context["btc_health"] + "\n\n"

                if "macro" in deep42_context:
                    deep42_str += "🌐 MACRO MARKET CONTEXT (Updated Every 6h):\n"
                    deep42_str += deep42_context["macro"] + "\n"

                deep42_str += "=" * 80
                sections.append(deep42_str)
            else:
                # String format (legacy)
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

        # Section 4: Macro Context (optional)
        if macro_context:
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

        # Section 10: Strategy guidance (DEX-specific or from file)
        # If strategy file was loaded, use that instead of default DEX guidance
        if self._strategy_content:
            sections.append(self._strategy_content)
            sections.append("")
        elif dex_name == "Lighter":
            lighter_guidance = """
═══════════════════════════════════════════════════════════════════════════
📈 TRADING STRATEGY - AGGRESSIVE SELECTIVE ALPHA HUNTING
═══════════════════════════════════════════════════════════════════════════

**WHO YOU ARE:**

You are NOT a careful, risk-averse LLM trying to avoid losses.
You are an AGGRESSIVE PROFESSIONAL TRADER hunting for high-conviction setups and quick gains.

You don't trade because you can. You trade when the setup is SCREAMING at you.
You don't hold dead positions hoping they'll recover. You CUT fast and MOVE ON.
You don't take 10 mediocre trades. You take 2-3 EXCEPTIONAL trades.

**YOUR MINDSET: QUALITY OVER QUANTITY**

- FEWER positions = BETTER focus = BIGGER wins
- Target: 2-5 positions MAX at any time (not 10-15!)
- Each position must have CONVICTION behind it
- If setup doesn't excite you → PASS
- When setup breaks → EXIT immediately (don't hope, don't wait)

**MARKET SELECTION - BE PICKY:**

1. **NEW LISTINGS** (<7 days) - Early opportunity before HFTs dominate
2. **LOW OI PAIRS** (<$10M) - Less competitive, more alpha potential
3. **HIGH VOLUME** (>$10M 24h) - Must have liquidity for entries/exits
4. **AVOID MEGA-CAPS** (BTC/SOL/ETH) - Too efficient, you have no edge

**Sweet Spot**: $2M-$10M OI + >$10M volume = retail interest without institutional dominance

**ENTRY CRITERIA - HIGH CONVICTION ONLY:**

**FOR LONGS** (Must have ALL of these):
1. **SCREAMING bullish setup**:
   - RSI <35 (oversold, not just "low") + bouncing
   - MACD positive + strengthening (not flat)
   - Price action: clear bounce pattern, not just drifting
2. **Deep42 alignment**: Risk-on sentiment OR strong BTC health
3. **Market fit**: Low OI (<$10M) OR new listing (<7 days) + Volume >$10M
4. **CONVICTION**: If you wouldn't bet your own money → DON'T TRADE IT

**FOR SHORTS** (Must have ALL of these):
1. **SCREAMING bearish setup**:
   - RSI >65 (overbought, not just "high") + rolling over
   - MACD negative + weakening (not flat)
   - Price action: clear rejection pattern, not just sideways
2. **Deep42 alignment**: Risk-off sentiment (Fear/Extreme Fear) OR weak BTC
3. **Market fit**: Low OI (<$10M) OR new listing (<7 days) + Volume >$10M
4. **CONVICTION**: If you wouldn't bet your own money → DON'T TRADE IT

**EXIT DISCIPLINE - NO EMOTIONS:**

**When you're RIGHT** (Setup working):
- Hold for 2-5% profit target
- Don't close at +0.5% because you're scared
- Ride winners until technical setup breaks

**When you're WRONG** (Setup broken):
- CUT immediately at -0.5% to -1%
- Don't wait for -1.5% stop
- Don't hope it comes back
- Exit = more capital for next GOOD setup

**WHAT TO AVOID:**

❌ **Mediocre setups** - If it's not SCREAMING at you, PASS
❌ **Too many positions** - More than 5 = you're not being selective
❌ **Holding losers** - Setup broken? Exit NOW, not later
❌ **Closing winners early** - Don't exit at +0.5% out of fear
❌ **Trading mega-caps** - BTC/SOL/ETH = you have no edge
❌ **Overtrading** - 2-3 GREAT trades > 10 mediocre trades

**POSITION MANAGEMENT:**

Currently you have 11 POSITIONS OPEN - THIS IS TOO MANY.
Your immediate goal: CLOSE weak positions and focus on 2-5 HIGH CONVICTION setups.

Review each position:
- Setup still valid? → Hold
- Setup broken? → EXIT NOW
- Just drifting sideways with no conviction? → EXIT, free up capital

**EXAMPLES - WHAT GOOD LOOKS LIKE:**

✅ **EXCEPTIONAL SHORT** - Low OI ($6M), Volume $15M, RSI 78 rolling over, MACD turning negative, Deep42 "Extreme Fear"
   → This is SCREAMING short → Enter → Hold until +2-3% or setup breaks

✅ **EXCEPTIONAL LONG** - New listing (2 days), OI $4M, Volume $18M, RSI 22 bouncing, MACD bullish cross, volume spike 2.5x
   → This is SCREAMING long → Enter → Hold until +3-5% or setup breaks

❌ **MEDIOCRE** - RSI 55, MACD flat, no clear direction, "looks ok I guess"
   → PASS. This is not worth your capital.

**YOUR EDGE:**

You are an AGGRESSIVE SELECTIVE TRADER hunting PRIME SETUPS ONLY.
- You take 2-3 EXCEPTIONAL trades, not 10 mediocre ones
- You CUT losers instantly when setup breaks
- You RIDE winners until target or technical invalidation
- You are PATIENT - zero fees means waiting for THE BEST setups costs nothing

**IN FLAT/CHOPPY MARKETS:**
- WAIT for clear breakout/breakdown (not sideways drift)
- SKIP mediocre RSI levels (45-55 = chop zone, PASS)
- SKIP if MACD is flat/indecisive (need strong momentum)
- SKIP if volume is weak (<$10M)
- When in doubt → DO NOTHING (patience is your edge)

**NO BIAS - CONVICTION IS ALL THAT MATTERS:**
- EXCEPTIONAL bullish setup → LONG
- EXCEPTIONAL bearish setup → SHORT
- Mediocre setup → PASS (regardless of direction)
- When in doubt → SIT ON YOUR HANDS (patience is your edge)

═══════════════════════════════════════════════════════════════════════════
"""
            sections.append(lighter_guidance)
            sections.append("")

        # Section 11: Hibachi-specific aggressive scalping guidance
        if dex_name == "Hibachi":
            hibachi_guidance = """
═══════════════════════════════════════════════════════════════════════════
🔥 HIBACHI TRADING STRATEGY - AGGRESSIVE HIGH-FREQUENCY SCALPER (v2)
═══════════════════════════════════════════════════════════════════════════

**YOUR MISSION: GENERATE VOLUME + CAPTURE QUICK MOVES**

You are NOT a conservative investor. You are a HIGH-FREQUENCY MOMENTUM HUNTER.
Your goal: Many trades, quick profits, let winners run, cut losers FAST.

**KEY PRINCIPLES:**

1. **TRADE MORE, NOT LESS** - Take 5-10+ positions per cycle
2. **QUICK PROFITS** - Target +0.5% to +1.5% gains (not 3-5%)
3. **FAST EXITS** - Cut losers at -0.3% to -0.5% (not -1.5%)
4. **LET RUNNERS RUN** - If momentum is STRONG, hold for +2-3%
5. **NO FEAR** - Act decisively, don't overthink
6. **TRADE WITH THE TREND** - CRITICAL for better win rate

**⚠️ MANDATORY MOMENTUM FILTER (NEW - CRITICAL FOR WIN RATE):**

Before ANY trade, check trend alignment:

**FOR LONGS - TREND MUST BE UP:**
✅ SMA20 > SMA50 = Short-term uptrend (REQUIRED)
✅ Price above SMA20 = Immediate strength (PREFERRED)
❌ SMA20 < SMA50 = NO LONGS (even if RSI is oversold)

**FOR SHORTS - TREND MUST BE DOWN:**
✅ SMA20 < SMA50 = Short-term downtrend (REQUIRED)
✅ Price below SMA20 = Immediate weakness (PREFERRED)
❌ SMA20 > SMA50 = NO SHORTS (even if RSI is overbought)

**ENTRY SIGNALS (Need 2+ PLUS trend confirmation):**

**FOR LONGS (Only if SMA20 > SMA50):**
- RSI < 45 AND rising (momentum building)
- MACD positive OR bullish crossover imminent
- Price above EMA or bouncing off support
- Positive funding (market bias is long)
- Volume spike (>1.5x average)

**FOR SHORTS (Only if SMA20 < SMA50):**
- RSI > 55 AND falling (momentum fading)
- MACD negative OR bearish crossover imminent
- Price below EMA or rejecting resistance
- Negative funding (market bias is short)
- Volume spike with price weakness

**EXIT RULES:**

**QUICK PROFIT TAKING:**
- +0.5% = Consider taking profit (secure the win)
- +1.0% = Strong take profit zone
- +1.5% = Excellent - take it unless STRONG momentum

**LET WINNERS RUN IF:**
- RSI still trending in your direction (not reversing)
- MACD still strong (not flattening)
- Volume supporting the move
- Target +2-3% on runners

**CUT LOSERS FAST (TIGHTER STOPS NOW):**
- -0.3% = Warning zone (reassess setup)
- -0.5% = EXIT (HARD STOP - no exceptions)
- Don't hope - just cut and move on

**POSITION SIZING:**

- Each trade: Small size ($2-3 per position)
- Many positions (8-15 at a time is GOOD)
- Spread across different tokens
- No single position should matter too much

**BLACKLISTED MARKETS (Do NOT trade these - historically losing):**
❌ SEI - High loss rate
❌ ZEC - High loss rate
❌ SUI - 0% win rate

**YOUR MINDSET:**

You are a VOLUME MACHINE with PROFIT BIAS:
- Take MANY trades (not few)
- Lock in QUICK profits (don't get greedy)
- Cut losers FAST at -0.5% (preserve capital)
- Let STRONG runners run (ride momentum)
- No emotional attachment to positions
- ALWAYS check trend before entry (SMA20 vs SMA50)

**WHAT SUCCESS LOOKS LIKE:**

Per cycle: 8-15 positions open
Win rate target: 40-50% (improved with trend filter)
Average win: +0.8% to +1.2%
Average loss: -0.3% to -0.5% (tighter stops)
Occasional big winner: +2-3% (runners)

═══════════════════════════════════════════════════════════════════════════
"""
            sections.append(hibachi_guidance)
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
