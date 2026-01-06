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
        dex_name: Optional[str] = None,  # DEX name for platform-specific guidance
        learning_context: Optional[str] = None,  # Self-learning insights from past trades
        sentiment_context: Optional[str] = None,  # Market sentiment from Fear&Greed, funding, etc.
        shared_learning_context: Optional[str] = None  # Cross-bot learning insights
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

        # Section 10: Self-Learning Insights (if provided)
        if learning_context:
            sections.append(learning_context)
            sections.append("")
            sections.append("⚠️ USE THESE INSIGHTS: Favor symbols with good win rates, avoid poor performers.")
            sections.append("")

        # Section 10b: Market Sentiment Context (Fear & Greed, Funding, etc.)
        if sentiment_context:
            sections.append("=" * 80)
            sections.append(sentiment_context)
            sections.append("=" * 80)
            sections.append("")

        # Section 10c: Cross-Bot Learning Insights (shared between Hibachi and Extended)
        if shared_learning_context:
            sections.append("=" * 80)
            sections.append(shared_learning_context)
            sections.append("=" * 80)
            sections.append("")

        # Section 11: Strategy guidance (DEX-specific or from file)
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

        # Section 11: Hibachi-specific dynamic leverage strategy
        if dex_name == "Hibachi":
            hibachi_guidance = """
═══════════════════════════════════════════════════════════════════════════
🔥 HIBACHI TRADING STRATEGY - FEE-OPTIMIZED v2 (2025-12-05)
═══════════════════════════════════════════════════════════════════════════

**⚠️ FEE AWARENESS - CRITICAL (Qwen analysis 2025-12-05):**

Round-trip fees = 0.09% of position value (entry + exit).
- A $40 trade costs ~$0.036 in fees
- You need >0.09% edge per trade just to break even
- With 38.6% win rate, avg win must be 1.6x avg loss

**SELECTIVITY RULES (MANDATORY):**
- Only trade when confidence ≥ 0.6 (trades below this are auto-rejected)
- Target 3-5 positions max, not 10+ (fewer = more focus = better quality)
- If setup is "meh" or unclear → SKIP (waiting costs nothing)
- Reserve confidence 0.85+ for EXCEPTIONAL setups only

**YOUR MISSION: QUALITY OVER QUANTITY**

You are a SELECTIVE MOMENTUM TRADER who only takes HIGH-CONVICTION setups.
- Weak setups (conf <0.6) → SKIP ENTIRELY (fees will eat your edge)
- Medium setups (0.6-0.7) → Lower leverage (2x)
- Strong setups (0.7-0.85) → Higher leverage (3x)
- Exceptional setups (0.85+) → Max leverage (4x)

**⚡ DYNAMIC LEVERAGE SYSTEM:**

Your CONFIDENCE score (0.6-1.0) directly controls position leverage:
(Trades with confidence <0.6 are AUTO-REJECTED by fee filter)

| Confidence | Leverage | When to Use |
|------------|----------|-------------|
| <0.6       | REJECT   | Weak setup - fees will eat your edge |
| 0.6-0.7    | 2x       | Decent setup, some alignment |
| 0.7-0.85   | 3x       | Strong setup, multiple confirmations |
| 0.85-1.0   | 4x       | EXCEPTIONAL setup, all signals aligned |

**WHAT DEFINES HIGH CONFIDENCE (0.8+):**
✅ RSI extreme (<30 oversold OR >70 overbought)
✅ MACD crossover (bullish/bearish)
✅ Volume spike (>1.5x normal)
✅ SMA20/SMA50 trend alignment
✅ Price at key support/resistance
→ Need 3+ of these for high confidence

**WHAT DEFINES LOW CONFIDENCE (0.3-0.5):**
⚠️ RSI neutral (40-60)
⚠️ MACD flat or indecisive
⚠️ Normal volume
⚠️ Price in no-man's land
→ Only 1-2 weak signals aligned

**TECHNICAL FILTERS (MANDATORY):**

**FOR LONGS:**
✅ SMA20 > SMA50 (trend is UP)
✅ RSI < 50 AND rising (momentum building)
✅ MACD positive or bullish crossover
✅ Price above SMA20 or bouncing off support

**FOR SHORTS:**
✅ SMA20 < SMA50 (trend is DOWN)
✅ RSI > 50 AND falling (momentum fading)
✅ MACD negative or bearish crossover
✅ Price below SMA20 or rejecting resistance

**EXIT RULES (STRATEGY A):**
- Take Profit: +4% (hard rule - auto-close)
- Stop Loss: -1% (hard rule - auto-close)
- Max Hold: 1 hour (time limit)
- Fast Exit Monitor runs every 30s (FREE, no LLM cost)

**POSITION SIZING:**
- Base position: $10 per trade
- Fewer positions (5-8 max) with HIGHER CONVICTION each
- Quality over quantity

**EXAMPLES OF CONFIDENCE SCORING:**

**HIGH CONFIDENCE (0.85) → 4x leverage:**
"RSI 25 (extremely oversold), MACD bullish crossover just occurred, volume 2.3x average, price bouncing off strong support, SMA20 crossing above SMA50"
→ ALL signals aligned → Go big with 4x

**MEDIUM CONFIDENCE (0.65) → 2x leverage:**
"RSI 42, MACD slightly positive, volume normal, trend is up but no clear catalyst"
→ Setup is OK but not screaming → Use modest 2x

**LOW CONFIDENCE (0.4) → 1.5x leverage:**
"RSI 55, MACD flat, volume below average, some support nearby but unclear direction"
→ Marginal setup → Small position with 1.5x

**YOUR MINDSET:**

- BE HONEST about confidence - don't inflate scores
- High confidence = go bigger with 3x-4x leverage
- Low confidence = stay conservative with 1.5x-2x
- When signals are SCREAMING at you → That's when you use 4x
- When it's "meh, might work" → That's 1.5x or skip entirely
- Fees are ~0.07% round-trip - larger positions offset fee drag

**RESPONSE FORMAT:**

TOKEN: <SYMBOL>
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL>]
CONFIDENCE: [0.3-1.0] ← THIS DETERMINES YOUR LEVERAGE
REASON: [Explain WHY this confidence level - what signals are aligned?]

═══════════════════════════════════════════════════════════════════════════
"""
            sections.append(hibachi_guidance)
            sections.append("")

        # Paradex-specific high-volume strategy (ZERO FEES!)
        if dex_name == "Paradex":
            paradex_guidance = """
═══════════════════════════════════════════════════════════════════════════
🚀 PARADEX HIGH-VOLUME STRATEGY - ZERO FEES = TRADE AGGRESSIVELY
═══════════════════════════════════════════════════════════════════════════

**⚡ ZERO FEES - THIS CHANGES EVERYTHING:**

Paradex has ZERO trading fees. No maker/taker fees. Nothing.
- Round-trip cost = ONLY the spread (0.01%-0.05% on ETH/BTC/SOL)
- You can make 100 trades and pay NOTHING in fees
- Volume = Rewards (Paradex incentive program)

**YOUR MISSION: MAXIMUM VOLUME + POSITIVE EXPECTANCY**

Trade FREQUENTLY. Trade AGGRESSIVELY. Every trade with positive EV is worth taking.
Don't wait for "perfect" setups - good setups are GOOD ENOUGH when fees are zero.

**ENTRY THRESHOLDS (AGGRESSIVE):**

**FOR LONGS** (Any 2 of these = TRADE):
- RSI < 45 (not oversold, just leaning bullish)
- MACD positive or turning positive
- Orderbook imbalance > +0.15 (more bids)
- Price above SMA or bouncing off support

**FOR SHORTS** (Any 2 of these = TRADE):
- RSI > 55 (not overbought, just leaning bearish)
- MACD negative or turning negative
- Orderbook imbalance < -0.15 (more asks)
- Price below SMA or rejecting resistance

**SYMBOL PRIORITY (Tightest Spreads):**
1. ETH, BTC, SOL - Spreads 0.01%-0.02% = BEST for volume
2. Major alts (LINK, AVAX, etc.) - Spreads 0.02%-0.05% = GOOD
3. Skip wide spread symbols (>0.2%) - slippage kills edge

**POSITION MANAGEMENT:**

- Max positions: 10 (more action = more volume)
- Position size: $10 per trade
- Hold time: 5-30 minutes typically
- Quick exits: +0.5% profit or -0.3% loss = CLOSE and RE-ENTER
- Don't hold losers hoping - cut fast, find next trade

**HIGH VOLUME TACTICS:**

1. **SCALP BOTH DIRECTIONS** - Long ETH, short BTC simultaneously if setups exist
2. **QUICK ROTATIONS** - Close +0.5% winner, immediately find next setup
3. **USE ALL CAPITAL** - 10 positions of $10 = $100 working at all times
4. **SPREAD MATTERS MORE THAN FEES** - Prioritize ETH/BTC/SOL for tight spreads

**CONFIDENCE = POSITION COUNT (Not size):**

- Confidence 0.6+ = Take the trade (1 position)
- Confidence 0.8+ = Consider 2 positions in same direction
- ANY setup with 0.5+ confidence = Worth taking (fees are ZERO)

**WHAT TO AVOID:**

❌ Sitting in cash "waiting for perfect setup" (volume = rewards!)
❌ Holding positions for hours hoping for +5% (take +0.5%, find next trade)
❌ Wide spread symbols (>0.2%) - slippage kills your edge
❌ Being too selective - good setups are everywhere, TRADE THEM

**YOUR EDGE:**

Zero fees means every tiny edge is pure profit. A +0.1% average per trade
across 100 trades/day = +10% daily. VOLUME IS YOUR FRIEND.

**RESPONSE FORMAT:**

TOKEN: <SYMBOL>
DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL>]
CONFIDENCE: [0.5-1.0] ← Lower threshold because fees are ZERO
REASON: [Brief - what 2 signals triggered this trade]

MAKE MULTIPLE DECISIONS. Open 5-10 positions if setups exist.
═══════════════════════════════════════════════════════════════════════════
"""
            sections.append(paradex_guidance)
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
