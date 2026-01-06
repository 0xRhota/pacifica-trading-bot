# Hopium Agents - Progress Tracker

**Last Updated:** 2026-01-06 (ongoing)

## Current Status: Paper Trade v4 - Realistic Position Sizing

### Paper Trade v5 - Now Running (17:19 UTC)
- **Position Sizing:** Dynamic, matches Extended executor logic
  - Formula: `balance × 0.8 × leverage` (3x-5x based on confidence)
  - With $100 balance & 0.8 conf: $100 × 0.8 × 4x = **$320 notional**
- **First Cycle Results:**
  - Hibachi: LONG BTC @ $92,468 ($320 notional)
  - Extended: LONG BTC @ $92,414 ($320 notional)
  - Paradex: LONG BTC @ $92,429 ($320 notional)
  - **Total Volume: $960** (3 positions)
- **Log:** `logs/unified_paper_trade.log`
- **Ends:** ~19:19 UTC

### Previous Paper Trade Issues Fixed
1. ~~`trade_tracker.py` syntax error (`p"""`)~~ ✅
2. ~~Extended API calling wrong method~~ ✅
3. ~~Position sizes too small ($10 instead of $300)~~ ✅
4. ~~LLM only picking cheapest exchange~~ ✅ (prompt updated for multi-exchange volume)

### Paper Trade v3 Results (~$10 positions - unrealistic)

| Exchange | Volume | P&L |
|----------|--------|-----|
| Hibachi | $10 | -$0.10 |
| Extended | $20 | -$0.04 |
| Paradex | $10 | -$0.06 |
| **Total** | $40 | **-$0.19** |

**Problem:** $10 positions don't reflect actual trading ($300 notional @ 10x leverage)

---

## Completed Tasks (2026-01-06)

### 1. Dual-Bot Learning Strategy Implementation
- [x] Created `llm_agent/data/sentiment_fetcher.py` - Fear & Greed Index, funding rates
- [x] Created `llm_agent/shared_learning.py` - Cross-bot insights sharing
- [x] Implemented `logs/shared_insights.json` - Shared state file
- [x] Updated `hibachi_agent/execution/strategy_a_exit_rules.py`:
  - TP: 8% (was 4%)
  - SL: 4% (was 2%)
  - Max Hold: 48h (was 2h)
  - Min Hold: 60 min
  - Max Trades/Day: 6
  - New "Cut Loser" rule: exit after 4h if underwater
- [x] Updated `extended_agent/execution/strategy_b_exit_rules.py` (matching changes)
- [x] Added sentiment context to LLM prompts for both bots
- [x] Added shared learning context to LLM prompts

### 2. Paradex Grid MM Fixes
- [x] **Task 8:** Auto-close existing position on startup
- [x] **Task 9:** Fixed inventory skew logic - now ONLY places orders that REDUCE position when >70% inventory
- [x] **Task 10:** Added strong trend filter (ROC > 2.0 bps pauses ALL grid activity)

### 3. Unified Paper Trading Script
- [x] Created `scripts/unified_paper_trade.py`
- Orchestrates all 3 exchanges with shared learning
- Real market data from Hibachi, Extended, Paradex
- LLM decisions using Qwen-Max

---

## Pending Tasks

### Pre-Deployment
- [ ] Complete 2-hour paper trade test
- [ ] Review paper trade results
- [ ] Test bots in dry-run mode

### Deployment (Task 11 - Awaiting User Approval)
```bash
# Hibachi
nohup python3 -u -m hibachi_agent.bot_hibachi --live --interval 600 > logs/hibachi_bot.log 2>&1 &

# Extended
nohup python3.11 -u -m extended_agent.bot_extended --live --strategy B --interval 300 > logs/extended_bot.log 2>&1 &

# Paradex Grid MM
python3.11 scripts/grid_mm_live.py
```

### Post-Deployment
- [ ] Monitor 48h performance
- [ ] Validate profit improvement vs. high-volume approach
- [ ] Tune parameters based on results

---

## Key Files Modified Today

| File | Change |
|------|--------|
| `llm_agent/data/sentiment_fetcher.py` | NEW - Fear & Greed, funding rates |
| `llm_agent/shared_learning.py` | NEW - Cross-bot insights |
| `logs/shared_insights.json` | NEW - Shared state |
| `hibachi_agent/execution/strategy_a_exit_rules.py` | 48h hold, 8% TP, 4% SL |
| `extended_agent/execution/strategy_b_exit_rules.py` | Matching profit-focused params |
| `hibachi_agent/bot_hibachi.py` | Added sentiment + shared learning |
| `extended_agent/bot_extended.py` | Added sentiment + shared learning |
| `llm_agent/llm/prompt_formatter.py` | Added sentiment_context, shared_learning_context params |
| `scripts/grid_mm_live.py` | Position close, inventory fix, momentum filter |
| `scripts/unified_paper_trade.py` | NEW - Paper trading orchestrator |

---

## Philosophy Change (2026-01-06)

**Old Approach:** High-volume trading (20+ trades/day)
- Problem: Fees + spread (~0.25%) make quick trades mathematically losing

**New Approach:** Profit-focused longer holds
- 6 trades/day max (quality over quantity)
- 8% TP, 4% SL (2:1 R/R minimum)
- 48h max hold (allow overnight/multi-day)
- Cut losers after 4h if underwater
- Bank profits, then periodically burn for volume

---

## Exchange Accounts

| Exchange | Balance | Status |
|----------|---------|--------|
| Hibachi | ~$100 | Active |
| Extended | ~$100 | Active |
| Paradex | ~$23 | Active |
