# Project Analysis

16,803 trades across 5 exchanges. 50+ strategy iterations. Oct 2025 to Jan 2026.

---

## Trade Data

**By Exchange:**
| Exchange | Trades | Win Rate | Best Direction |
|----------|--------|----------|----------------|
| Lighter | 12,665 | 44.7% | SHORT (49.4%) |
| Extended | 1,590 | 41.8% | SHORT (45.6%) |
| Hibachi | 1,579 | 37.3% | LONG (38.9%) |
| Pacifica | 486 | 22.4% | paused |
| Paradex | 483 | 37.9% | LONG (39.5%) |

**Confidence vs Actual Win Rate:**
| Confidence | Expected | Actual | Gap |
|------------|----------|--------|-----|
| 0.6 | 60% | 46.2% | -14% |
| 0.7 | 70% | 44.7% | -25% |
| 0.8 | 80% | 44.2% | -36% |
| 0.9 | 90% | 51.7% | -38% |

0.8 confidence trades won less often than 0.7. LLM is overconfident.

**Best Symbols:**
| Symbol | P&L | Trades | WR |
|--------|-----|--------|-----|
| FARTCOIN | +$79.72 | 24 | 33.3% |
| BTC-USD | +$73.25 | 868 | 37.8% |
| XPL | +$69.36 | 37 | 24.3% |

**Avoid These:**
| Symbol | P&L | Trades | Note |
|--------|-----|--------|------|
| BTC | -$39,161 | 290 | different pair than BTC-USD |
| BNB | -$13,235 | 741 | 45.9% WR, still losing |
| BCH | -$13,100 | 716 | 48.6% WR, still losing |
| ZEC | -$3,022 | 1,068 | most traded loser |

---

## Strategy Iterations

### Prompt Versions (v1-v9)

| Version | Date | Approach | Result |
|---------|------|----------|--------|
| v1_baseline_conservative | Oct 30 | wait for clear conditions | too passive |
| v2_aggressive_swing | Oct 31 | prefer action | overtrading |
| v3_longer_holds | Oct 31 | 1.5-3% targets | better |
| v4_strategic_thinking | Oct 31 | more reasoning | marginal |
| v4_momentum_strategy | Nov 8 | momentum signals | mixed |
| v5_swing_trading | Nov 9 | swing focus | tested |
| v6_aggressive_scalper | Nov 24 | quick trades | fees killed it |
| v6_high_volume | Nov 27 | volume focus | mixed |
| v7_alpha_arena_discipline | Nov 24 | discipline rules | better |
| v8_alpha_arena_pure_pnl | Nov 24 | P&L focus | good |
| v9_qwen_enhanced | Nov 24 | 5-signal scoring | +22.3% in 17 days |

### Live Strategy Switches (19 total)

| # | Date | Strategy | Change | Result |
|---|------|----------|--------|--------|
| 1 | Nov 13 | deep42-v1 | added Deep42 sentiment | baseline |
| 2 | Nov 14 | deep42-v2-patient | 30min holds, 2% targets | helped |
| 3 | Nov 15 | technicals-only-v1 | removed Deep42 from exits | better |
| 4 | Nov 15 | longer-holds-v1 | guidance-based holds | mixed |
| 5 | Nov 17 | longer-holds-v1-no-deep42 | removed macro override | cleaner |
| 6 | Nov 17 | low-competition-swing-v1 | target <$50M OI | niche |
| 7 | Nov 17 | low-comp-swing-short-bias | forced SHORT bias | worse |
| 8 | Nov 17 | hard-exit-rules-v1 | hard exits override LLM | major improvement |
| 9 | Nov 18 | neutral-adaptive-v1 | removed hardcoded bias | better |
| 10 | Nov 18 | aggressive-selective-v1 | 2-5 positions max | better |
| 11 | Nov 19 | light-short-bias-v1 | light SHORT lean | current (Lighter) |
| 12 | Dec 4 | fee-optimizer-v1 | Qwen fee analysis | better |
| 13 | Dec 4 | dynamic-leverage-v1 | confidence-based leverage | better |
| 14 | Dec 4 | btc-scalper-copy-v1 | copy whale trader | tested |
| 15 | Dec 5 | fee-optimized-v2 | 10min intervals | better |
| 16 | Dec 5 | aggressive-sizing-v6 | 4-6x leverage | mixed |
| 17 | Dec 8 | deep42-bias-v7 | re-enable Deep42 for bias | tested |
| 18 | Dec 15 | pairs-trade-v2-dynamic | ETH/BTC pairs | current (Extended) |
| 19 | Dec 15 | v9-qwen-enhanced | 5-signal scoring | current (Hibachi) |

### Grid MM Evolution (8 versions)

| Version | P&L/$10k | Change | Result |
|---------|----------|--------|--------|
| v1 | +$0.48 | 1 bps spread | baseline |
| v2 | -$2.02 | wider 2.5 bps | worse |
| v3 | -$1.94 | volatility adjust | too slow |
| v4 | -$1.91 | inventory skewing | marginal |
| v5 | -$1.47 | force close 5 bps | locks losses |
| v6 | -$1.26 | preemptive pause | better |
| v7 | -$0.77 | 20s min pause | efficient |
| v8 | +$1.81 | full context, 15s pause | profitable |

Wider spreads made it worse (v2-v4). Prevention beats reaction.

---

## What Works

1. Hard exit rules: +2% take profit, -1.5% stop loss, 2h min hold
2. 5-signal scoring: RSI + MACD + Volume + Price Action + OI confluence, require score >= 3.0
3. Asymmetric R:R: 30% win rate works if winners are 3x losers
4. 2-5 positions max
5. SHORT bias on Lighter/Extended

## What Doesn't Work

1. Deep42 for exit decisions (causes early exits on winners)
2. Sizing up on high confidence (0.8 conf = 44% actual WR)
3. Wider Grid MM spreads
4. Time-based Grid refresh (use 0.25% price trigger instead)
5. Hardcoded directional bias
6. BCH, BNB, ZEC trading

## Failed Experiments

| Experiment | Problem |
|------------|---------|
| Funding rate arbitrage | needs $10k+ capital |
| Copy trading (whale following) | latency, whale traps |
| Mean reversion (RSI < 30 = buy) | crypto trends hard, oversold goes more oversold |
| High-frequency scalping | fees destroy profits |

---

## Current Active Strategies

| Bot | Exchange | Strategy |
|-----|----------|----------|
| hibachi_agent | Hibachi | v9-qwen-enhanced |
| lighter_agent | Lighter | light-short-bias-v1 |
| extended_agent | Extended | Strategy D (pairs) |
| grid_mm_live | Paradex | Grid MM v8 |

---

## Key Files

| Purpose | Location |
|---------|----------|
| Strategy history | `logs/strategy_switches.log` |
| Winning prompt | `llm_agent/prompts_archive/v9_qwen_enhanced.txt` |
| Trade data | `logs/trades/*.json` |
| Self-learning state | `logs/strategies/self_improving_llm_state.json` |
| Grid MM history | `research/strategies/GRID_MM_EVOLUTION.md` |
