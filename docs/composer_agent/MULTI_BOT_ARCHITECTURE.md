# Multi-Bot Architecture & Prompt System Design

**Date**: 2025-10-31  
**Purpose**: Design document for multi-bot system with easy prompt swapping

---

## Overview

**Goal**: Run multiple trading bots simultaneously, each with different strategies/prompts, easy prompt customization, and multi-timeframe macro context for swing trading.

---

## 1. Multi-Timeframe Macro Context

### Current Problem

**Issue**: Macro context focuses on long-term trends (BTC dominance "high for months"), not actionable for swing trading.

**Example**:
- Current: "BTC dominance is 60% (high)" ← Not useful, this is a months-long trend
- Needed: "BTC dominance dropped 2% today, volume up 150% on SOL" ← Actionable for swing trading

### Required Changes

#### 1.1 Use Multi-Timeframe Deep42 Analysis

**Current**: Only fetches single long-term analysis  
**Needed**: Fetch daily, weekly, and long-term separately

**Implementation**: 
- Already exists: `MacroContextFetcher._fetch_deep42_multi_analysis()`
- Currently unused: `get_macro_context()` only calls `_fetch_deep42_analysis()`
- **Fix**: Call `_fetch_deep42_multi_analysis()` instead

**Questions asked**:
- **Daily**: "What are the major cryptocurrency news, catalysts, and events happening TODAY?"
- **Weekly**: "What are the key crypto events and catalysts expected THIS WEEK?"
- **Market State**: "What is the current state of the crypto market?"

#### 1.2 Add Timeframe-Specific Metrics

**Daily Metrics** (24h changes):
- BTC dominance change (24h delta)
- Volume spikes (tokens with >50% volume increase)
- Funding rate changes (24h delta)
- Price action (24h change for major tokens)

**Weekly Metrics** (7d trends):
- BTC dominance trend (rising/falling/stable)
- Volume trends (increasing/decreasing)
- Funding rate trends (most markets positive/negative)
- Momentum indicators (RSI trends)

**Long-Term Metrics** (keep existing):
- Overall market state
- Fear & Greed Index
- Market cap trends

#### 1.3 Format Macro Context with Sections

**New Format**:
```
======================================================================
MACRO CONTEXT (Multi-Timeframe for Swing Trading)
Last Updated: 2025-10-31 08:53 UTC
======================================================================

=== DAILY CONTEXT (Swing Trading Focus) ===
Deep42 Daily Analysis (Cambrian Network):
[Events, catalysts, news happening TODAY]

Daily Metrics:
- BTC Dominance 24h Change: +0.5% (from 60.2% to 60.7%)
- Volume Spikes: SOL +150%, ETH +80%, PENGU +200%
- Funding Rate Changes: SOL -0.01%, ETH +0.005%
- Price Action: BTC +2.1%, ETH +1.8%, SOL +3.2%

=== WEEKLY CONTEXT (Swing Trading Focus) ===
Deep42 Weekly Analysis (Cambrian Network):
[Events, catalysts, news expected THIS WEEK]

Weekly Trends:
- BTC Dominance 7d Trend: Declining (-1.2% over 7 days)
- Volume Trend: Increasing (most altcoins showing higher volume)
- Funding Rate Trend: Mostly positive (bullish sentiment)
- Momentum: SOL, ETH showing strong momentum

=== LONG-TERM CONTEXT (Background) ===
Deep42 Market State Analysis (Cambrian Network):
[Overall market state, macro trends]

Long-Term Metrics:
- Fear & Greed Index: 29/100 (Fear) 😰
- BTC Dominance: High (60%+) but declining trend
- Market Cap 24h: -1.2% 📉
- Overall Sentiment: Bearish short-term, neutral long-term

======================================================================
```

**Prompt Guidance**: For swing trading, focus on DAILY and WEEKLY context. Long-term context is background only.

---

## 2. Prompt Template System

### 2.1 Directory Structure

```
llm_agent/
├── prompts/
│   ├── base.md                    # Base prompt (current)
│   ├── swing_trading.md          # Swing trading focus (daily/weekly)
│   ├── aggressive.md              # More aggressive entries
│   ├── conservative.md            # Capital preservation
│   └── contrarian.md              # Contrarian entries
└── llm/
    └── prompt_formatter.py        # Loads templates
```

### 2.2 Template Format

**Template File** (`prompts/swing_trading.md`):
```markdown
# Trading Instructions

{{deep42_daily_context}}

{{deep42_weekly_context}}

{{market_data_section}}

{{positions_section}}

## Decision Guidelines

**Your Trading Style: Swing Trading (Daily/Weekly Timeframes)**

Focus on:
- **Daily context**: Events happening TODAY, 24h price movements, volume spikes
- **Weekly context**: Events THIS WEEK, 7-day trends, momentum indicators
- **Long-term context**: Background only - don't let months-long trends prevent action

Key Metrics for Swing Trading:
- Daily volume changes (>50% increase = strong signal)
- BTC dominance daily changes (not absolute value)
- Funding rate 24h changes
- Price momentum (24h and 7d)

Decision Making:
- Consider daily/weekly context FIRST
- Long-term trends are background context only
- Don't wait for perfect setups - swing trading means capturing short-term moves
- BTC dominance "high for months" is not actionable - focus on daily/weekly changes

## Risk Management

- Maximum position size: ${{position_size}} per trade
- Maximum positions: {{max_positions}} open at once
- Prefer trades with clear daily/weekly catalysts
- Exit when daily/weekly context changes

## Decision Format

DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL> | NOTHING]
REASON: [Your reasoning citing DAILY/WEEKLY context + market data in 2-3 sentences]
```

### 2.3 Template Variables

**Available Variables**:
- `{{deep42_daily_context}}` - Daily Deep42 analysis
- `{{deep42_weekly_context}}` - Weekly Deep42 analysis
- `{{deep42_market_state}}` - Long-term market state
- `{{market_data_section}}` - Formatted market table
- `{{positions_section}}` - Open positions
- `{{position_size}}` - Position size from config
- `{{max_positions}}` - Max positions from config

**Python Implementation**:
```python
class PromptFormatter:
    def __init__(self, template_name: str = "base"):
        self.template_path = f"llm_agent/prompts/{template_name}.md"
        self.template = self._load_template()
    
    def format_trading_prompt(self, **kwargs):
        # Replace variables in template
        prompt = self.template.format(**kwargs)
        return prompt
```

---

## 3. Multi-Bot Architecture

### 3.1 Bot Configuration System

**Directory Structure**:
```
llm_agent/
├── bot_configs/
│   ├── swing_trader.json         # Swing trading bot config
│   ├── aggressive_bot.json        # Aggressive bot config
│   ├── conservative_bot.json      # Conservative bot config
│   └── contrarian_bot.json        # Contrarian bot config
└── bot_llm.py                     # Main bot (accepts config)
```

**Config Format** (`bot_configs/swing_trader.json`):
```json
{
  "bot_name": "swing_trader",
  "prompt_template": "swing_trading",
  "position_size": 30.0,
  "max_positions": 3,
  "check_interval": 300,
  "timeframe_focus": "swing",
  "log_file": "logs/swing_trader.log",
  "dry_run": false,
  "description": "Swing trading bot focused on daily/weekly timeframes"
}
```

**Config Format** (`bot_configs/aggressive_bot.json`):
```json
{
  "bot_name": "aggressive_bot",
  "prompt_template": "aggressive",
  "position_size": 40.0,
  "max_positions": 5,
  "check_interval": 300,
  "timeframe_focus": "both",
  "log_file": "logs/aggressive_bot.log",
  "dry_run": false,
  "description": "Aggressive bot with higher position limits"
}
```

### 3.2 Running Multiple Bots

**Command Line**:
```bash
# Bot 1: Swing trading
python3 -m llm_agent.bot_llm --config bot_configs/swing_trader.json --live &

# Bot 2: Aggressive
python3 -m llm_agent.bot_llm --config bot_configs/aggressive_bot.json --live &

# Bot 3: Conservative
python3 -m llm_agent.bot_llm --config bot_configs/conservative_bot.json --live &
```

**Docker Compose** (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  swing_trader:
    build: .
    command: python -m llm_agent.bot_llm --config bot_configs/swing_trader.json --live
    env_file: .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  aggressive_bot:
    build: .
    command: python -m llm_agent.bot_llm --config bot_configs/aggressive_bot.json --live
    env_file: .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  conservative_bot:
    build: .
    command: python -m llm_agent.bot_llm --config bot_configs/conservative_bot.json --live
    env_file: .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### 3.3 Position Management

**Per-Bot Position Limits**:
- Each bot tracks its own positions separately
- Total positions = sum of all bot positions
- Global limit: Configurable max total positions across all bots

**Example**:
- `swing_trader`: Max 3 positions
- `aggressive_bot`: Max 5 positions
- **Total possible**: 8 positions (if within global limit)

**Trade Tracking**:
- Each bot logs to its own log file
- Trade tracker includes `bot_name` field
- Can view trades per bot: `python3 scripts/view_trades.py --bot swing_trader`

---

## 4. Implementation Plan

### Phase 1: Multi-Timeframe Macro Context (Priority: HIGH)

**Tasks**:
1. Modify `MacroContextFetcher.get_macro_context()` to use `_fetch_deep42_multi_analysis()`
2. Add daily BTC dominance calculation (24h change)
3. Add weekly BTC dominance calculation (7d trend)
4. Add volume spike detection (24h volume changes)
5. Add funding rate change tracking (24h changes)
6. Format macro context with daily/weekly/long-term sections
7. Test with swing trading focus

**Files to Modify**:
- `llm_agent/data/macro_fetcher.py`

**Estimated Impact**: High - Makes macro context actionable for swing trading

### Phase 2: Prompt Template System (Priority: HIGH)

**Tasks**:
1. Create `/llm_agent/prompts/` directory
2. Extract current prompt to `base.md`
3. Create `swing_trading.md` template (emphasizes daily/weekly)
4. Create variant templates (aggressive, conservative, contrarian)
5. Modify `PromptFormatter` to load templates from files
6. Add template variable substitution
7. Update `bot_llm.py` to accept `--prompt-template` parameter

**Files to Modify**:
- `llm_agent/llm/prompt_formatter.py`
- `llm_agent/bot_llm.py`
- Create: `llm_agent/prompts/*.md`

**Estimated Impact**: High - Enables easy prompt customization

### Phase 3: Multi-Bot Architecture (Priority: MEDIUM)

**Tasks**:
1. Create `/llm_agent/bot_configs/` directory
2. Create config JSON files for each bot type
3. Modify `bot_llm.py` to accept `--config` parameter
4. Add bot name/ID to logs and trade tracking
5. Update position limits to be per-bot
6. Add per-bot log file support
7. Test running multiple bots simultaneously

**Files to Modify**:
- `llm_agent/bot_llm.py`
- `llm_agent/execution/trade_executor.py`
- Create: `llm_agent/bot_configs/*.json`

**Estimated Impact**: Medium - Enables strategy diversification

### Phase 4: Documentation (Priority: MEDIUM)

**Tasks**:
1. Update `docs/PROMPT_CUSTOMIZATION.md` with template system
2. Create `docs/MULTI_BOT_SETUP.md`
3. Create `docs/MACRO_CONTEXT_TIMEFRAMES.md`
4. Update `USER_REFERENCE.md` with new commands
5. Update `CLAUDE.md` with new architecture

**Files to Create/Update**:
- `docs/MULTI_BOT_SETUP.md` (NEW)
- `docs/MACRO_CONTEXT_TIMEFRAMES.md` (NEW)
- `docs/PROMPT_CUSTOMIZATION.md` (UPDATE)
- `USER_REFERENCE.md` (UPDATE)
- `CLAUDE.md` (UPDATE)

---

## 5. Example: Swing Trading Bot

### 5.1 Prompt Template

**File**: `llm_agent/prompts/swing_trading.md`

```markdown
# Trading Instructions - Swing Trading Bot

## Timeframe Focus: Daily/Weekly (Swing Trading)

You are a swing trader focusing on daily and weekly timeframes. 
Long-term trends are background context only - don't let them prevent action.

## Macro Context Analysis

### Daily Context (Primary Focus)
{{deep42_daily_context}}

**Daily Metrics**:
- BTC Dominance 24h Change: {{btc_dom_daily_change}}
- Volume Spikes: {{volume_spikes}}
- Funding Rate Changes: {{funding_changes_daily}}

**Action**: Focus on daily catalysts and 24h price movements.

### Weekly Context (Secondary Focus)
{{deep42_weekly_context}}

**Weekly Trends**:
- BTC Dominance 7d Trend: {{btc_dom_weekly_trend}}
- Volume Trend: {{volume_trend_weekly}}
- Momentum Indicators: {{momentum_indicators}}

**Action**: Consider weekly events and 7-day trends.

### Long-Term Context (Background Only)
{{deep42_market_state}}

**Long-Term Metrics**:
- Fear & Greed Index: {{fear_greed_index}}
- Overall Market State: {{market_state}}

**Action**: Background context only - don't let months-long trends prevent daily/weekly trades.

## Market Data

{{market_data_section}}

## Open Positions

{{positions_section}}

## Decision Guidelines

**Swing Trading Strategy**:
- Focus on DAILY and WEEKLY context first
- Look for daily catalysts (events TODAY)
- Consider weekly trends (events THIS WEEK)
- Don't wait for perfect setups - swing trading captures short-term moves
- BTC dominance "high for months" is NOT actionable - focus on daily/weekly CHANGES

**Entry Signals**:
- Daily volume spikes (>50% increase)
- Daily BTC dominance changes (not absolute value)
- Weekly momentum indicators
- Daily/weekly catalysts from Deep42

**Exit Signals**:
- Daily context changes (new events/catalysts)
- Weekly trend reversal
- Position target reached

## Risk Management

- Maximum position size: ${{position_size}} per trade
- Maximum positions: {{max_positions}} open at once
- Prefer trades with clear daily/weekly catalysts
- Exit when daily/weekly context changes

## Decision Format

DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL> | NOTHING]
REASON: [Your reasoning citing DAILY/WEEKLY context + market data in 2-3 sentences]
```

### 5.2 Bot Config

**File**: `llm_agent/bot_configs/swing_trader.json`

```json
{
  "bot_name": "swing_trader",
  "prompt_template": "swing_trading",
  "position_size": 30.0,
  "max_positions": 3,
  "check_interval": 300,
  "timeframe_focus": "swing",
  "log_file": "logs/swing_trader.log",
  "dry_run": false,
  "description": "Swing trading bot focused on daily/weekly timeframes"
}
```

### 5.3 Running the Bot

```bash
# Start swing trading bot
python3 -m llm_agent.bot_llm --config bot_configs/swing_trader.json --live

# View logs
tail -f logs/swing_trader.log

# View decisions
python3 scripts/view_decisions.py --bot swing_trader
```

---

## 6. Benefits

### 6.1 Multi-Timeframe Context

**Before**:
- "BTC dominance is high (60%)" ← Not actionable
- "Market is bearish" ← Too vague

**After**:
- "BTC dominance dropped 2% today, SOL volume up 150%" ← Actionable
- "Daily catalysts: SOL upgrade announcement TODAY" ← Clear signal

### 6.2 Easy Prompt Customization

**Before**:
- Edit Python code
- Restart bot
- Hard to test variations

**After**:
- Edit markdown file
- Restart bot with new template
- Easy A/B testing

### 6.3 Multi-Bot Support

**Before**:
- Single bot, single strategy
- Hard to diversify

**After**:
- Multiple bots, different strategies
- Easy strategy diversification
- Independent position limits

---

## 7. Next Steps

1. ✅ **Document requirements** (this document)
2. ⏳ **Implement multi-timeframe macro context**
3. ⏳ **Build prompt template system**
4. ⏳ **Add multi-bot architecture**
5. ⏳ **Test with swing trading bot**
6. ⏳ **Deploy multiple bots**

---

**End of Design Document**

