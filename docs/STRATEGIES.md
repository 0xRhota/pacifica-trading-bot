# Strategies

This document explains each trading strategy: what it does, how it works, its parameters, and which files control it.

---

## How the Bot Works

Every bot follows the same basic cycle:

1. **Fetch market data** (price, RSI, MACD, volume, funding rate, OI)
2. **Build an LLM prompt** with market data + strategy context
3. **Query the LLM** (Qwen via OpenRouter) for trading decisions
4. **Validate decisions** (check symbol exists, position limits, etc.)
5. **Execute trades** via the exchange SDK
6. **Monitor positions** for exit conditions (TP/SL/time)
7. **Repeat** after interval (default 600s)

The **strategy** controls:
- What data goes into the prompt
- What filters are applied to LLM decisions
- How exits are handled (LLM discretion vs hard rules)

---

## Strategy F: Self-Improving LLM

**Flag:** `--strategy F`
**Default for:** Hibachi
**File:** `hibachi_agent/execution/strategy_f_self_improving.py`
**Prompt:** `llm_agent/prompts_archive/v9_qwen_enhanced.txt`

### What It Does

Tracks every trade outcome and builds dynamic filters based on performance. Instead of hardcoded rules like "never short SOL", it learns from actual results.

### How It Works

1. Records every trade: symbol, direction (LONG/SHORT), confidence, entry price, exit price, P&L
2. Analyzes performance by dimensions (symbol, direction, confidence level)
3. Auto-generates filters:
   - **Block** combinations with <30% win rate (e.g., "SOL SHORT blocked")
   - **Reduce** size for <40% win rate combinations
4. Adds performance context to LLM prompt so the model sees its own track record

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `position_size` | $10 | USD per trade |
| `review_interval` | 10 | Analyze performance every N trades |
| `rolling_window` | 50 | Number of recent trades to analyze |
| `auto_apply_filters` | true | Automatically apply learned filters |
| `log_dir` | logs/strategies | Where to save state |

### State File

`logs/strategies/self_improving_llm_state.json` - Contains learned filters, trade history, performance stats.

### Example Filter Output

```
BLOCKED COMBINATIONS (DO NOT TRADE):
- SOL_SHORT: 25% win rate (12 trades) - BLOCKED
- BNB_LONG: 28% win rate (18 trades) - BLOCKED

HIGH RISK (reduce size by 50%):
- ETH_SHORT: 38% win rate (24 trades) - CAUTION
```

---

## Strategy D: Pairs Trade

**Flag:** `--strategy D`
**Best for:** Hibachi, Extended
**File:** `hibachi_agent/execution/strategy_d_pairs_trade.py`

### What It Does

Opens opposite positions on two correlated assets (ETH vs BTC). The LLM decides which one to long based on relative strength. Goal: generate volume while staying near break-even.

### How It Works

1. LLM analyzes ETH and BTC market data
2. LLM picks which asset is "stronger" (more likely to outperform)
3. Bot opens LONG on the stronger asset, SHORT on the weaker
4. Holds for a fixed time (default 60 min)
5. Closes both positions
6. Logs combined P&L and repeats

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `position_size_usd` | $100 | USD per leg (total exposure = 2x this) |
| `hold_time_seconds` | 3600 | How long to hold before closing (60 min) |
| `long_asset` | ETH/USDT-P | First asset in pair |
| `short_asset` | BTC/USDT-P | Second asset in pair |

### Log File

`logs/strategy_d_pairs.log` - Contains every pair trade with both legs' P&L.

### Example Cycle

```
PAIRS TRADE: OPENING NEW PAIR
  Long: ETH/USDT-P ($50.00)
  Short: BTC/USDT-P ($50.00)
  Total exposure: $100.00
  Reasoning: ETH showing stronger RSI recovery

[60 minutes later]

PAIRS TRADE COMPLETE
  Long PnL:  +$1.23
  Short PnL: -$0.45
  NET PnL:   +$0.78
```

---

## Strategy G: Low-Liquidity Hunter

**Flag:** `--strategy G`
**Best for:** Hibachi
**File:** `hibachi_agent/execution/strategy_g_low_liq_hunter.py`

### What It Does

Targets volatile, low-liquidity pairs where retail hasn't priced in moves yet. Avoids BTC/ETH/SOL (too efficient). Uses trailing stops to let winners run.

### How It Works

1. Filters to target pairs only (HYPE, PUMP, VIRTUAL, ENA, DOGE, SEI, etc.)
2. Calculates entry score based on 6 weighted signals
3. Requires score >= 3.0 to enter
4. Uses trailing stop: after +1.5%, trails at 0.75% behind peak
5. Self-learns signal effectiveness and adjusts weights

### Target Pairs

**Tier 1 (most volatile):** HYPE, PUMP, VIRTUAL, ENA, PROVE, XPL
**Tier 2 (moderate):** DOGE, SEI, SUI, BNB, ZEC, XRP
**Avoid:** BTC, ETH, SOL

### Entry Signals (need 3+)

| Signal | Long Condition | Short Condition |
|--------|---------------|-----------------|
| RSI | < 35 (oversold) | > 65 (overbought) |
| MACD | Bullish crossover | Bearish crossover |
| Volume | > 2x average | > 2x average |
| EMA | Price above EMA20 | Price below EMA20 |
| VWAP | Price near/below VWAP | Price near/above VWAP |
| Funding | < -0.03% (shorts crowded) | > +0.05% (longs crowded) |

### Exit Rules

| Rule | Value |
|------|-------|
| Stop loss | -2% |
| Take profit | +3% |
| Trailing trigger | +1.5% |
| Trailing stop | 0.75% behind peak |
| Max hold | 120 minutes |
| Daily loss limit | -$20 |

### State File

`logs/strategies/strategy_g_state.json` - Contains signal weights, daily P&L.

---

## Strategy A: Hard Exit Rules

**Flag:** `--strategy A` (or used internally by F/G)
**File:** `hibachi_agent/execution/strategy_a_exit_rules.py`

### What It Does

Enforces hard exit rules that override LLM discretion. The LLM decides entries, but exits are mechanical.

### Exit Rules

| Rule | Value | Description |
|------|-------|-------------|
| Take profit | +4% | Immediate close when hit |
| Stop loss | -2% | Immediate close when hit |
| Max hold | 2 hours | Close regardless of P&L |
| Min hold | 5 minutes | Block LLM from closing too early |
| Daily limit | 20 trades | Stop trading after limit |

### Why Hard Rules?

From testing: LLM tends to exit winners too early and hold losers too long. Hard rules fix this.

---

## Strategy C: Copy Whale

**Flag:** `--strategy C`
**Best for:** Extended
**File:** `extended_agent/execution/strategy_c_copy_whale.py`

### What It Does

Mirrors a proven whale trader's BTC/ETH/SOL portfolio allocation. Proportional sizing: if whale has 64% in BTC, you allocate 64% of your balance to BTC.

### Target Whale

```
Address: 0x023a3d058020fb76cca98f01b3c48c8938a22355
Name: Multi-Asset Scalper
Account: ~$28M
Activity: ~28 trades/min
Unrealized: +$966K on BTC/ETH/SOL
```

### How It Works

1. Polls whale's Hyperliquid positions every 5 minutes
2. Calculates whale's % allocation to BTC, ETH, SOL
3. Compares to our current allocation
4. Rebalances if allocation differs by > 5%
5. Executes trades on Extended DEX

### Example

```
Whale account: $28.8M
  - BTC: $18.4M (64% of portfolio)
  - ETH: $4.3M (15%)
  - SOL: $5.8M (20%)

Your account: $77
  - BTC target: $77 x 64% = $49.28
  - ETH target: $77 x 15% = $11.55
  - SOL target: $77 x 20% = $15.40
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `COPY_ASSETS` | BTC, ETH, SOL | Assets to copy |
| `REBALANCE_THRESHOLD_PCT` | 5.0 | Only rebalance if difference > 5% |

---

## LLM Prompts

The LLM prompt tells the model how to analyze data and make decisions. Located in `llm_agent/prompts_archive/`.

### Active Prompt: v9_qwen_enhanced.txt

Based on the Alpha Arena Season 1 winner strategy (+22.3% in 17 days).

**Core Rules:**
1. Score every signal 0-1, sum them, require >= 3.0 to trade
2. Use funding rate as contrarian indicator
3. Asymmetric R:R: risk 1% to make 2-4%
4. Quality over quantity (avg 2.5 trades/day)

**Signal Scoring:**

| Signal | 1.0 Point | 0.5-0.7 Points | 0 Points |
|--------|-----------|----------------|----------|
| RSI | < 35 or > 65 | 35-45 or 55-65 | 45-55 (neutral) |
| MACD | Clear crossover | Just turning | Flat/choppy |
| Volume | > 2x average | 1.2-2x average | < 1.2x average |
| Price Action | Support bounce / breakout | Near key level | Mid-range |
| OI + Price | Rising OI + price direction | Falling OI | No data |

**Response Format:**

```
DECISION: BUY ETH
CONFIDENCE: 0.82
SIGNAL_SCORE: 3.8/5.0
SCORING_BREAKDOWN: RSI=0.8, MACD=0.8, Vol=0.7, PA=0.8, OI=0.7
STOP_LOSS: -1.0%
TARGET: +3.0%
R:R RATIO: 3:1
REASON: RSI=38 bouncing from oversold, MACD bullish crossover...
```

### Prompt History

| Version | Approach | Result |
|---------|----------|--------|
| v1 | Conservative, wait for clear conditions | Too passive |
| v2 | Aggressive swing | Overtrading |
| v3 | Longer holds, 1.5-3% targets | Better |
| v6 | Scalping | Fees killed it |
| v7 | Discipline rules | Improved |
| v8 | P&L focus over win rate | Good |
| v9 | 5-signal scoring (current) | +22.3% in 17 days |

---

## Changing Strategies

### Via Command Line

```bash
# Hibachi with Strategy F (self-improving)
python3 -m hibachi_agent.bot_hibachi --live --strategy F --interval 600

# Hibachi with Strategy D (pairs)
python3 -m hibachi_agent.bot_hibachi --live --strategy D --interval 600

# Hibachi with Strategy G (low-liq hunter)
python3 -m hibachi_agent.bot_hibachi --live --strategy G --interval 600
```

### Via Code

The strategy is selected in `bot_hibachi.py` line 232-259 based on the `--strategy` flag. Each strategy class is initialized there.

### Changing the Prompt

Edit `llm_agent/llm/prompt_formatter.py` to change which prompt file is loaded, or swap prompts with:

```bash
./scripts/swap_prompt.sh v9_qwen_enhanced
```

---

## Strategy Comparison

| Strategy | LLM Cost | Best For | Risk Level |
|----------|----------|----------|------------|
| F (Self-Improving) | Medium | General trading | Medium |
| D (Pairs) | Low | Volume generation | Low |
| G (Low-Liq Hunter) | Medium | High volatility | High |
| A (Hard Exits) | Medium | Discipline | Medium |
| C (Copy Whale) | None | Following proven trader | Medium |

---

## Files Reference

| Component | File |
|-----------|------|
| Strategy F (Self-Improving) | `hibachi_agent/execution/strategy_f_self_improving.py` |
| Strategy D (Pairs) | `hibachi_agent/execution/strategy_d_pairs_trade.py` |
| Strategy G (Low-Liq) | `hibachi_agent/execution/strategy_g_low_liq_hunter.py` |
| Strategy A (Hard Exit) | `hibachi_agent/execution/strategy_a_exit_rules.py` |
| Strategy C (Copy Whale) | `extended_agent/execution/strategy_c_copy_whale.py` |
| Core Self-Improving Logic | `core/strategies/self_improving_llm.py` |
| Prompt Formatter | `llm_agent/llm/prompt_formatter.py` |
| Model Client | `llm_agent/llm/model_client.py` |
| v9 Prompt | `llm_agent/prompts_archive/v9_qwen_enhanced.txt` |
| Strategy State (F) | `logs/strategies/self_improving_llm_state.json` |
| Strategy State (G) | `logs/strategies/strategy_g_state.json` |
| Pairs Log (D) | `logs/strategy_d_pairs.log` |
