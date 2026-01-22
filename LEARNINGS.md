# Hopium Agents - Learnings Log

**Purpose**: Central location for all strategy learnings with hard evidence and specific references.
**Last Updated**: 2026-01-22 (HIB-001 through HIB-007 added)

> For detailed strategy history, see [research/Learnings.md](research/Learnings.md)

---

## Current Goal

**Find the optimal market conditions to run the most optimized grid strategy.**

Key questions we're trying to answer:
1. Is there ONE grid strategy that works across all conditions?
2. Or do we need to swap/adjust strategy based on market regime?
3. When should we run grid MM vs other strategies (LLM directional, pairs trade)?

**The Core Hypothesis**: Grid MM can work, but we need to identify:
- Which market conditions favor grid MM (ranging, low volatility)
- Which conditions require switching to directional strategies (trending)
- Optimal parameters per regime (spread, ROC threshold, pause duration)

**What We Know So Far**:
- Grid was working, then went off the rails
- Part market conditions (volatility spike), part our fault (tight spreads)
- v10 overcorrected with 15 bps spreads (too wide, no fills)

---

## Exchange P&L Comparison (2026-01-15)

| Exchange | P&L | Volume | P&L per $10k | Notes |
|----------|-----|--------|--------------|-------|
| Nado | -$80 | ~$50k | **-$16** | Best performer |
| Hibachi | -$160 | ~$50k | -$32 | 2x worse than Nado |
| Extended | ~-$160 | ~$50k | -$32 | Similar to Hibachi |
| Paradex | TBD | TBD | TBD | Need data |

**Key Finding**: Nado performing 2x better per volume than Hibachi/Extended.

**Possible Reasons**:
- Different fee structures?
- Different assets (ETH on Nado vs BTC on others)?
- Different market microstructure?
- Dynamic capital fix applied to Nado first?

**Knowledge Gap**: Need to dig into WHY Nado is outperforming. Is it the exchange, the asset, or something in our config?

---

## Recent Learnings

### Grid MM Refresh Logic Bugs - Orders Go Stale (2026-01-22)

**Problem**: Both Nado and Paradex Grid MM have 0 fills for 1.5+ hours despite running. Investigation revealed orders become stale and spread doesn't update.

**Issue 1: Dynamic Spread Not Updating (Nado)**
- **Location**: `scripts/grid_mm_nado_v8.py` line 426
- **Bug**: `_calculate_dynamic_spread()` only called inside `_place_grid_orders()`
- **Trigger**: `_place_grid_orders()` only called when `fills > 0` OR `price_move >= 0.5%`
- **Result**: With 0 fills and slow price moves (<0.5%), spread NEVER updates
- **Evidence**: ROC at +27.8 bps but spread stuck at 15.0 bps (should be 30 bps per config)
- **Log**: `[24.2m] $2,997.25 | ROC: +27.8bps | Spread: 15.0bps | LIVE`

**Issue 2: Stale Orders Never Refreshed (Paradex)**
- **Location**: `scripts/grid_mm_live.py` lines 675-680
- **Bug**: 0.5% price reset threshold too conservative
- **Scenario**: Orders placed at $90,025.95 at 08:10. Current price $89,951 (0.08% move)
- **Result**: Orders $60-90 from market, will never fill, but aren't refreshed
- **The "no active orders" check doesn't help** because stale orders are still OPEN on exchange

**Why Hibachi Grid MM Works**:
- Hibachi uses time-based refresh (every 30s)
- Cancels and re-places orders every cycle
- Dynamic spread updates correctly (10 bps → 15 bps as ROC increased)

**Recommendations**:
1. Add time-based refresh (e.g., every 5-10 minutes) regardless of price/fills
2. OR reduce price reset threshold to 0.1-0.2%
3. OR check if orders are "stale" (too far from current mid price)
4. Move `_calculate_dynamic_spread()` call OUTSIDE of `_place_grid_orders()` so spread updates every cycle

**Knowledge Gap**: Should time-based refresh replace price-based refresh, or supplement it?

---

### CRITICAL: Nado Grid MM v14 - Fix Constant Reset Loop (2026-01-21)

**Problem**: Nado Grid MM was in a constant reset loop - placing orders, immediately "inferring" them as filled, resetting, repeat. No orders were resting on the book.

**Root Causes Found** (3 bugs):

1. **Wrong success check**: Code used `result.get('success')` but SDK returns `result.get('status') == 'success'`. Orders were never tracked.
   - File: `scripts/grid_mm_nado_v8.py` lines 501, 541
   - Fix: Changed to `result.get('status') == 'success'`

2. **Inventory ratio reset**: When inventory > 80%, triggered grid reset every cycle. With 176% inventory, bot couldn't settle.
   - Fix: Removed `inventory_ratio > 0.8` from reset conditions. REDUCE LONG/SHORT MODE already handles high inventory by placing one-sided orders.

3. **Inferred fill logic**: Orders that "disappeared" from `get_orders()` were counted as fills. On Nado, API has propagation delays - orders aren't immediately visible. This caused false fill detection.
   - Fix: Removed "inferred fill" logic. Only count fills with explicit FILLED/CLOSED status.

**Additional fix**: Added 3-cycle cooldown after placing orders before checking fills.

**Result**: Orders now rest on the book. Grid MM stable. Tested and confirmed 1 SELL order at $2886.90 resting on exchange.

**Files Changed**:
- `scripts/grid_mm_nado_v8.py` - Lines 501, 541, 555-599, 645-670

**Key Insight**: Nado API is eventually consistent - don't assume orders are immediately visible or that disappeared orders were filled.

---

### CRITICAL: Nado Grid MM v15 - ROC Parameters Causing Zero Trades (2026-01-21)

**Problem**: Nado Grid MM running 5+ hours with zero volume. Orders placed but immediately paused.

**Root Causes Found** (2 issues):

1. **ROC threshold too aggressive (20 bps)**:
   - v13 had `roc_threshold_bps=20.0` to "pause earlier"
   - But normal market swings are 5-25 bps
   - Result: PAUSE BUY or PAUSE SELL triggered constantly
   - Evidence: Logs showed "PAUSE SELL orders (ROC: +20.59 bps)" every few seconds

2. **ROC window mismatch (1 min vs 3 min)**:
   - Code used `prices[-60]` (1-minute lookback)
   - But LEARNINGS.md v12 fix specified 3-minute window (180 samples)
   - Result: ROC swings too fast, spread never stabilizes

**Compounding Factor**: Pre-existing LONG position at 101% inventory
   - With `buy_mult=0.0` (can't buy more)
   - When ROC > 20 bps positive, PAUSE SELL kicks in
   - Result: Can't place ANY orders

**Fix Applied** (`scripts/grid_mm_nado_v8.py`):
```python
# Line 719: ROC threshold back to 50 bps
roc_threshold_bps=50.0,  # Was 20.0

# Line 324-328: ROC window back to 3 minutes
if len(self.price_history) < 180:  # Was 60
    return 0.0
past = prices[-180]  # Was prices[-60]
```

**Lesson**: ROC threshold and window must be calibrated together. Lower threshold (20 bps) needs shorter window (10s) OR higher threshold (50 bps) with longer window (3 min). Mixing them causes constant triggering.

**Files Changed**:
- `scripts/grid_mm_nado_v8.py` - Lines 324, 328, 719

---

### CRITICAL: P&L Tracking Must Use Exchange Data (2026-01-16)

**Problem**: Bot-calculated P&L (balance_now - balance_at_start) gave wildly wrong numbers (+$49 when actual was -$13.84). This has been a recurring problem for months.

**Root Cause**: Bot P&L tracking doesn't account for:
- Unrealized P&L changes
- Position mark-to-market
- Timing of deposits/withdrawals
- Funding payments vs trading P&L

**The CORRECT Way - Nado**:
Use the Archive API `matches` endpoint which provides per-trade:
- `realized_pnl` - Actual realized P&L from closing positions
- `fee` - Trading fees paid

**Implementation**:
```python
# Added to dexes/nado/nado_sdk.py
async def get_pnl(self, hours: int = 24) -> Dict:
    # Queries Archive API matches endpoint
    # Returns: realized_pnl, fees, net_pnl, trade_count
```

**Validation**:
| Source | Reported P&L |
|--------|--------------|
| Bot log (WRONG) | +$49.88 |
| Exchange UI | -$13.84 |
| SDK get_pnl() | **-$13.83** ✓ |

**Rule**: NEVER trust bot-calculated P&L. ALWAYS use exchange API data.

**Files Changed**:
- `dexes/nado/nado_sdk.py` - Added `get_pnl()` and `_archive_query()` methods

---

### CRITICAL: Nado Grid Must Use POST_ONLY Orders (2026-01-16)

**Problem**: Nado grid bot was paying 3.5x higher fees than necessary. Analysis of 500 trades showed 42% were executing as TAKER instead of MAKER.

**Evidence** (last 500 trades on Nado):
| Type | Trades | Fees | Fee/Trade |
|------|--------|------|-----------|
| MAKER | 288 | $3.88 | $0.0135 |
| TAKER | 212 | $10.12 | $0.0477 |

Taker fee rate (0.035%) is 3.5x higher than maker (0.01%).

**Root Cause**: Grid bot was using `order_type="LIMIT"` but Nado SDK maps unknown types to "DEFAULT" which can cross the spread and execute as taker. The SDK supports:
- `DEFAULT` = Can cross spread (taker fills allowed)
- `IOC` = Immediate or Cancel
- `FOK` = Fill or Kill
- `POST_ONLY` = Maker only, rejected if would cross spread

**Impact**:
- Expected cost (all maker): ~$4.25 in fees
- Actual cost: $14.03 in fees
- **Extra $10 paid due to taker fills**
- Net P&L would have been -$15 instead of -$23 (35% improvement)

**Fix Applied**:
```python
# scripts/grid_mm_nado_v8.py lines 488, 528
order_type="POST_ONLY"  # Was "LIMIT" - now maker-only
```

**Lesson**: Always use POST_ONLY for grid MM to guarantee maker fills. Orders that would cross spread get rejected, which is what we want - we'd rather not fill than fill as taker.

**Files Changed**:
- `scripts/grid_mm_nado_v8.py` - Changed to POST_ONLY for both buy/sell limit orders

---

### CRITICAL: ROC Window Must Match Spread Thresholds (2026-01-19)

**Problem**: Dynamic spread (v12) was stuck at 1.5-3.0 bps even during real trends. Nado lost $17 in one day despite 100% maker rate.

**Root Cause**: ROC window mismatch
- Spread thresholds designed for: 5/15/30/50 bps
- Actual ROC window: 10 seconds (rarely exceeds 5 bps)
- Result: Spread never widens, bot gets run over by slow trends

**Evidence** (from logs):
```
14:55:26 | SPREAD WIDENED: 1.5 → 3.0 bps (ROC: +5.2)
14:55:30 | SPREAD TIGHTENED: 3.0 → 1.5 bps (ROC: +4.0)  # 4 seconds later!
```
Spread flip-flopped every few seconds, never staying wide.

**Historical Context**:
- v5 designed 10-second ROC for pause decisions (thresholds: 1-2 bps)
- v12 added spread thresholds 5-50 bps but reused the 10-second window
- Mismatch: Higher thresholds need longer window to trigger

**Math**:
| Move Speed | 10-sec ROC | 3-min ROC | Spread |
|------------|------------|-----------|--------|
| 0.5%/30min | 0.3 bps | 5 bps | 3.0 bps |
| 0.5%/10min | 0.8 bps | 15 bps | 6.0 bps |
| 0.3%/5min | 1.0 bps | 18 bps | 6.0 bps |

**Fix Applied**:
- `price_history` maxlen: 30 → 360 (6 minutes buffer)
- ROC lookback: `prices[-10]` → `prices[-180]` (3-minute window)
- Minimum samples: `< 10` → `< 180`

**Expected Impact**: Spread will now widen and STAY wide during moderate trends, preventing adverse selection losses.

**Files Changed**:
- `scripts/grid_mm_nado_v8.py` - ROC window fix (lines 91, 318-327)
- `scripts/grid_mm_live.py` - ROC window fix (lines 82, 282-294)
- `tests/test_dynamic_spread.py` - Added ROC window tests

---

### CRITICAL: Dynamic Balance Fetching at Trade Time (2026-01-20)

**Problem**: Nado and Paradex grid bots cached `self.capital` once at startup. When deposits/withdrawals occurred, the bot continued using stale capital values for inventory calculations, leading to incorrect position sizing.

**Evidence**: User deposited $50 to Nado. Bot would NOT automatically adjust position sizes because it used the cached startup balance.

**Root Cause**: Unlike Hibachi/Extended which fetch balance dynamically, Nado/Paradex set capital once:
```python
# BAD - stale after deposits/withdrawals
self.capital = self.initial_balance  # Set at startup, never updated
max_inventory = self.capital * (self.max_inventory_pct / 100)
```

**The CORRECT Way** (from Hibachi/Extended):
```python
# GOOD - fresh balance at trade time
account_balance = await self._fetch_account_balance()
position_size_usd = account_balance * base_pct * leverage
```

**Fix Applied**:

Nado (`scripts/grid_mm_nado_v8.py`):
```python
# In _place_grid_orders() - fetch fresh balance
current_balance = await self.sdk.get_balance() or self.capital
max_inventory = current_balance * (self.max_inventory_pct / 100)

# In main loop - fetch fresh balance for inventory ratio
loop_balance = await self.sdk.get_balance() or self.capital
max_inventory = loop_balance * (self.max_inventory_pct / 100)
```

Paradex (`scripts/grid_mm_live.py`):
```python
# In _place_grid_orders() - fetch fresh balance
account = await self.client.account.get()
current_balance = float(account.account_value) if account else self.capital
max_inventory = current_balance * (self.max_inventory_pct / 100)

# In main loop - same pattern
loop_account = await self.client.account.get()
loop_balance = float(loop_account.account_value) if loop_account else self.capital
```

**HARD RULE**: ALL bots must fetch balance at trade time, NOT cache at startup. This ensures:
1. Deposits are automatically reflected in position sizing
2. Withdrawals don't cause oversized positions
3. No manual restart required after balance changes

**Files Changed**:
- `scripts/grid_mm_nado_v8.py` - Dynamic balance in `_place_grid_orders()` and main loop
- `scripts/grid_mm_live.py` - Dynamic balance in `_place_grid_orders()` and main loop

---

### Hibachi Leverage Reduction - Match Extended (2026-01-20)

**Problem**: Hibachi executor had "Dynamic Leverage System v7" with 10-15x leverage while Extended used conservative 3-5x. Analysis showed Hibachi had 36 state sync issues ("No positions but have active_trade - clearing") vs only 3 on Extended.

**Root Cause**: High leverage (up to 15x) on Hibachi was designed for "volume points farming" but caused API/state issues when used with Strategy D pairs trading. The bot would try to place large orders, encounter issues, and lose track of position state.

**Evidence**: Comparing hibachi_executor.py vs extended_executor.py:
- Hibachi v7: 10-15x leverage, base_pct 60-80%
- Extended: 3-5x leverage, base_pct 80%, $100-$1000 limits

**Fix Applied** (`hibachi_agent/execution/hibachi_executor.py`):
```python
# OLD (v7 - aggressive)
if confidence < 0.7:
    leverage = 10.0
elif confidence < 0.8:
    leverage = 15.0  # Too aggressive!
...

# NEW (v8 - conservative, match Extended)
BASE_LEVERAGE = 3.0
MAX_LEVERAGE = 5.0
if confidence < 0.5:
    leverage = BASE_LEVERAGE
elif confidence < 0.7:
    leverage = BASE_LEVERAGE + 0.5
elif confidence < 0.85:
    leverage = BASE_LEVERAGE + 1.0
else:
    leverage = MAX_LEVERAGE
```

**Result**: Hibachi now uses same leverage tiers as Extended (3-5x instead of 10-15x).

---

### Dynamic Spread Implementation (2026-01-15)

**Problem**: Fixed spread approaches don't adapt to market conditions. Tight spreads get run over during volatility (adverse selection). Wide spreads miss fills during calm periods.

**Solution**: Dynamic spread that automatically adjusts based on ROC (Rate of Change) volatility.

**Implementation (v12)**:
| ROC (abs) | Spread | Rationale |
|-----------|--------|-----------|
| 0-5 bps | 1.5 bps | Calm market, tight spreads capture fills |
| 5-15 bps | 3 bps | Low volatility, balanced |
| 15-30 bps | 6 bps | Moderate volatility, protect from adverse selection |
| 30-50 bps | 10 bps | High volatility, wide protection |
| >50 bps | PAUSE | Existing pause logic handles extreme trends |

**Why These Bands**:
- Market spread on Paradex is ~0.6-0.8 bps
- At 1.5 bps we're ~2.5x market spread (competitive but profitable)
- At 3 bps we're ~5x market spread (still get fills)
- Beyond 6 bps, fill rate drops significantly
- ROC of 50 bps typically indicates real trend (pause is correct)

**Evidence**:
- Statistical analysis: 1 bps spread → ~18 fills/hour; 2 bps → ~6 fills/hour
- Fill probability decreases non-linearly with distance from inside quote
- ROC already calculated in `_calculate_roc()` method, reused for spread

**Files Changed**:
- `scripts/grid_mm_nado_v8.py` (v12)
- `scripts/grid_mm_live.py` (v12)
- `tests/test_dynamic_spread.py` (25 tests)

**Logging**:
```
📊 SPREAD WIDENED: 1.5 → 3.0 bps (ROC: +7.2)
📊 SPREAD TIGHTENED: 6.0 → 3.0 bps (ROC: +4.1)
```

---

### Grid MM Spread Overcorrection (2026-01-14/15)

**Problem**: After Grid MM v8 showed tight spreads (1.5 bps) losing money due to adverse selection, we implemented Qwen-recommended v10 parameters with 15 bps spreads. Result: almost zero fills.

**Evidence**:
- Nado bot: No trades for hours (logs/grid_mm_nado.log, 2026-01-14)
- Paradex bot: Minimal fills after v10 update

**Root Cause Analysis**:
| Parameter | v8 (tight) | v10 (wide) | Problem |
|-----------|------------|------------|---------|
| Spread | 1.5 bps | 15 bps | Too wide - no fills |
| ROC threshold | 1.0 bps | 50 bps | Good - filters trends |
| Pause duration | 15s | 300s | Good - avoids whipsaws |

**Qwen Consultation (2026-01-15)**:
> "With ROC-based pausing already filtering trends, 15 bps is overcorrection. During stable periods when trading IS active, your quotes are too uncompetitive to get filled. Recommendation: 8 bps spread."

**Resolution**: Reduced spread from 15 bps to 8 bps (v11, deployed 2026-01-15 12:25)

**Knowledge Gap**: Need more data on optimal spread by asset and volatility regime. Monitoring v11 fill rates.

---

### Strategy D Pairs Trade Bug - Hard Exit Rules (2026-01-15)

**Problem**: Hibachi Strategy D (delta neutral pairs trade) was leaving orphaned positions. The bot would close one leg (e.g., ETH long) while leaving the other leg (BTC short) open, breaking delta neutrality.

**Evidence** (logs/hibachi_bot.log):
```
Executing decision: CLOSE ETH/USDT-P - HARD RULE: CUT LOSER: 16.08h underwater (P/L: -0.36%)
```

**Root Cause**: The main bot loop's hard exit rules (`StrategyAExitRules.check_should_force_close()`) were applied to ALL positions including pairs trade legs. When one leg triggered "CUT LOSER" (4+ hours underwater), it closed independently.

**Why This Breaks Delta Neutral**:
- Pairs trade = Long one asset + Short the other (equal $ amounts)
- If market moves, one leg profits while the other loses (expected!)
- Closing just the losing leg exposes the remaining position to directional risk

**Fix Applied**:
```python
# hibachi_agent/bot_hibachi.py lines 439-455
# Skip hard exit rules for pairs trade positions when Strategy D active
pairs_trade_symbols = {self.pairs_strategy.ASSET_A, self.pairs_strategy.ASSET_B}
if symbol in pairs_trade_symbols:
    continue  # Skip hard exit check - pairs close together via Strategy D
```

**Additional Note**: FastExitMonitor was already correctly disabled for Strategy D (line 1166-1170).

**Lesson**: Delta neutral strategies need special handling - both legs must be treated as a single unit for exit decisions.

**Files Changed**:
- `hibachi_agent/bot_hibachi.py` (skip hard exits for pairs positions)

---

### Dynamic Capital vs Hardcoded Settings (2026-01-14)

**Problem**: Nado bot stuck in REDUCE SHORT MODE at -149% inventory, not placing orders.

**Evidence** (logs/grid_mm_nado.log):
```
Capital mismatch: config said $90, actual balance $40.59
With $40 capital and $60 position = 150% inventory
```

**Root Cause**: Hardcoded `capital=90.0` parameter didn't match actual account balance. Bot calculated inventory % against wrong capital.

**Fix Applied**:
```python
# scripts/grid_mm_nado_v8.py line 144-146
# Use actual balance as capital (dynamic, not hardcoded)
self.capital = self.initial_balance
logger.info(f"Account balance: ${self.initial_balance:.2f}")
```

**Lesson**: Bots should ALWAYS pull capital from exchange balance, never use hardcoded values.

**Files Changed**:
- `scripts/grid_mm_nado_v8.py`
- `scripts/grid_mm_live.py` (Paradex)

---

### Exchange Min Notional Requirements (2026-01-14)

**Problem**: Nado bot orders being silently skipped.

**Evidence**: Orders with $30 size never appearing on exchange.

**Root Cause**: Nado requires $100 minimum notional per order.

| Exchange | Min Notional | Notes |
|----------|--------------|-------|
| Nado | $100 | Discovered 2026-01-14 |
| Paradex | $10 | Per order |
| Lighter | ~$1 | Very low |
| Hibachi | ~$10 | Approximate |

**Fix Applied**: Set `order_size_usd=100.0` for Nado bot.

**Lesson**: Always verify exchange minimum order sizes before deployment.

---

### Buy High, Sell Low Pattern (2025-12 Analysis)

**Problem**: Grid MM bots consistently buying at higher prices than selling.

**Evidence** (from trade log analysis):
```
Average BUY price: $97,847.23
Average SELL price: $97,822.09
Difference: -$25.14 (buying higher than selling!)
```

**Root Cause**: Adverse selection. When bot's buy order fills, it means price is falling INTO the bid. When sell order fills, price is rising INTO the ask.

**The Grid MM Paradox**:
- Get filled = usually on wrong side of move
- Don't get filled = no profit
- Solution: Pause during trends, only trade in ranges

**References**:
- `research/strategies/GRID_MM_EVOLUTION.md`
- Trade analysis scripts in `scripts/analyze_*.py`

---

## Strategy Performance Summary

### Grid MM Evolution

| Version | P&L per $10k | Spread | Key Change |
|---------|--------------|--------|------------|
| v1 | +$0.48 | 1 bps | Baseline |
| v2 | -$2.02 | 2.5 bps | Wider (failed) |
| v3 | -$1.94 | Variable | Volatility adjust (failed) |
| v4 | -$1.91 | 2 bps | Inventory skew (marginal) |
| v5 | -$1.47 | 1.5 bps | Force close (better) |
| v6 | -$1.26 | 1.5 bps | Preemptive pause (better) |
| v7 | -$0.77 | 1.5 bps | Min pause 20s (better) |
| v8 | +$1.81 | 1.5 bps | Full context (profitable) |
| v9 | TBD | 3.5 bps | 0.25% price trigger |
| v10 | Low fills | 15 bps | Overcorrected |
| v11 | TBD | 8 bps | Qwen recommended |
| v12 | TBD | **1.5-10 bps** | **Dynamic based on ROC** |

**Key Insight**: Spread width is not the answer. Trend detection (ROC + pause) is.

---

### LLM Confidence vs Actual Win Rate

From 16,803 trades (Oct 2025 - Jan 2026):

| Confidence | Expected WR | Actual WR | Gap |
|------------|-------------|-----------|-----|
| 0.6 | 60% | 46.2% | -13.8% |
| 0.7 | 70% | 44.7% | -25.3% |
| 0.8 | 80% | 44.2% | -35.8% |
| 0.9 | 90% | 51.7% | -38.3% |

**Lesson**: LLM confidence is poorly calibrated. Don't size positions based on confidence.

---

## What Works

1. **ROC-based trend detection** for Grid MM (pause during trends)
2. **Hard exit rules** for LLM bots (+2%/-1.5%, 2h min hold)
3. **SHORT bias on Lighter/Extended** (49.4% WR for shorts vs 41.8% longs)
4. **5-signal scoring** (v9-qwen-enhanced) for entry filtering
5. **Dynamic capital** from exchange balance
6. **Strategy D pairs trade** (delta neutral, LLM picks direction)
7. **Dynamic spread based on ROC** (v12 - tight in calm, wide in volatile)
8. **Exchange API P&L tracking** (matches endpoint with realized_pnl + fees)
9. **POST_ONLY orders for Grid MM** (Nado - reject rather than fill as taker)
10. **Dynamic balance at trade time** (fetch fresh balance, never cache at startup)
11. **Momentum confirmation for LLM entries** (HIB-001 - require short-term momentum matches signal)
12. **Trailing stops for winners** (HIB-002 - breakeven at +4%, trail at +6%)
13. **Win rate tracking per asset** (HIB-004 - auto-block symbols <30% WR)
14. **Indicator caching** (HIB-005 - 50% LLM cost reduction)

## What Doesn't Work

1. **Wider Grid MM spreads** (v2-v4 proved it, v10 re-proved it)
2. **Deep42 for exit decisions** (causes early panic exits)
3. **Sizing based on LLM confidence**
4. **Trading BCH, BNB, ZEC** (low liquidity, high spreads)
5. **Time-based Grid refresh** (use 0.25% price trigger instead)
6. **Hardcoded capital settings**
7. **Bot-calculated P&L** (balance_now - balance_at_start is WRONG - use exchange API)
8. **Cached startup balance** (must fetch fresh balance at trade time - deposits/withdrawals won't be reflected otherwise)

---

## Knowledge Gaps

- [ ] Optimal spread by asset volatility (need regime classification)
- [ ] Funding rate prediction accuracy
- [ ] Long-term Grid MM profitability with 8 bps spread
- [ ] Strategy D pairs trade performance data (recently started)
- [ ] Nado exchange reliability (new integration)

---

## File References

| Topic | Location |
|-------|----------|
| Detailed strategy history | `research/Learnings.md` |
| Grid MM evolution | `research/strategies/GRID_MM_EVOLUTION.md` |
| Trade analysis | `scripts/analyze_all_trades.py` |
| LLM prompts archive | `llm_agent/prompts_archive/` |
| Strategy switches log | `logs/strategy_switches.log` |

---

*This file must be updated with every significant learning. Include dates, evidence, and specific file references.*

---

### Bot Strategy Switchover Procedure (2026-01-21)

**Problem**: When switching from one strategy to another (e.g., Strategy D → Grid MM), any open positions from the old strategy become orphaned.

**Proper Switchover Steps**:
1. **Check open positions** before stopping old bot
2. **Close all positions** from old strategy
3. **Cancel all open orders** from old strategy  
4. **Stop old bot**
5. **Verify clean state** (0 positions, 0 orders)
6. **Start new bot**

**Quick Check Command** (Hibachi):
```python
positions = await sdk.get_positions()
balance = await sdk.get_balance()
# Ensure positions list is empty before starting new strategy
```

**What NOT to do**: Just kill the old bot and start the new one - this leaves orphaned positions that the new strategy doesn't know about.

---

### Hibachi Dual Strategy Improvements (2026-01-22)

**Context**: Optimizing Hibachi Grid MM + LLM Directional system to improve profitability.

**Starting State**:
- Grid MM (BTC): $47.22 balance, -$2.80 PnL, zero fills in 218 minutes
- LLM Bot: 40% win rate, BTC SHORT just closed +7.99% (166h hold)
- DOGE blocked at 9% win rate

---

#### HIB-001: Momentum Confirmation for LLM Entries

**Problem**: LLM signals sometimes contradicted short-term price momentum, leading to immediate adverse moves after entry.

**Solution**: Calculate 5-minute price momentum and require it to match LLM direction before entering.

**Implementation** (`hibachi_agent/bot_hibachi.py`):
```python
def calculate_momentum(self, kline_df, lookback_minutes=5):
    """Calculate 5-minute price momentum."""
    # Uses close prices over lookback period
    # Returns: momentum_pct, direction (BULLISH/BEARISH/NEUTRAL)

def check_momentum_confirmation(self, momentum_data, llm_action):
    """Require momentum matches LLM signal."""
    # BULLISH = momentum > +0.05%
    # BEARISH = momentum < -0.05%
    # NEUTRAL = allows weak confirmation
```

**Logic**:
- Momentum > +0.05% = BULLISH
- Momentum < -0.05% = BEARISH
- Otherwise = NEUTRAL (weak, still allows trade)

**Expected Impact**: Fewer false signals by requiring short-term momentum confirmation.

---

#### HIB-002: Trailing Stop for Winning Trades

**Problem**: Profitable trades (like the BTC SHORT at +7.99%) could give back gains during pullbacks. No mechanism to lock in profits.

**Evidence**: BTC SHORT closed at +7.99% after 166 hours - could have exited at +9% or more with trailing stop.

**Solution**: Implement trailing stop that ratchets upward as profit grows.

**Implementation** (`hibachi_agent/execution/fast_exit_monitor.py`):
```python
BREAKEVEN_TRIGGER_PCT = 4.0   # Move to breakeven at +4%
TRAILING_TRIGGER_PCT = 6.0    # Start trailing at +6%
TRAILING_DISTANCE_PCT = 2.0   # Trail 2% below peak

def check_trailing_stop(self, symbol, pnl_pct):
    """Evaluate and update trailing stops for winning trades."""
    # Tracks peak P&L, ratchets stop upward only
```

**Logic**:
1. Position hits +4% → breakeven lock activated (exit if drops to 0%)
2. Position hits +6% → trailing stop at +4%
3. Position hits +8% → trailing stop raises to +6%
4. If price drops to trailing stop → exit

**Expected Impact**: Lock in profits on winning trades (BTC SHORT would have locked in +5.99% minimum).

---

#### HIB-003: Grid MM Spread Optimization

**Problem**: Grid MM had zero fills in 360 cycles over 218 minutes. Orders were being cancelled every 30s before fills.

**Evidence** (`logs/grid_mm_hibachi.log`):
- Balance dropped $50.02 → $47.22 (PnL: -$2.80)
- No fill events logged
- Dynamic spread ranged 10-25 bps

**Root Cause**: Spreads too wide. CLAUDE.md confirms: "Wider Grid MM spreads DON'T work (v2-v4 proved it)"

**Fix Applied** (`scripts/grid_mm_hibachi.py`): Reduced all spreads by 20%

| ROC (abs) | Old Spread | New Spread |
|-----------|------------|------------|
| 0-5 bps   | 10 bps     | 8 bps      |
| 5-10 bps  | 15 bps     | 12 bps     |
| 10-20 bps | 20 bps     | 16 bps     |
| > 20 bps  | 25 bps     | 20 bps     |

**Expected Impact**: Increased fill rate while maintaining trend protection.

---

#### HIB-004: Win Rate Tracking Per Asset

**Problem**: DOGE was blocked at 9% win rate, but no systematic way to identify and block underperforming assets.

**Solution**: Track win rate per symbol and auto-block assets with <30% WR over 10+ trades.

**Implementation** (`llm_agent/self_learning.py`):
```python
def get_blocked_symbols(self, hours=168, min_trades=10, block_threshold=0.30):
    """Get symbols that should be blocked due to poor performance."""

def is_symbol_blocked(self, symbol, hours=168, min_trades=10, block_threshold=0.30):
    """Check if specific symbol is blocked."""

def log_win_rate_summary(self, hours=168):
    """Generate win rate summary for logging."""
```

**Integration** (`hibachi_agent/bot_hibachi.py`):
- Logs win rate summary during self-learning check-in (every 30 min)
- Blocks trades on symbols with <30% WR (10+ trade minimum)

**Example Output**:
```
ETH/USDT-P: 48% WR (12/25 trades, $+15.50) - WATCH
SOL/USDT-P: 40% WR (4/10 trades, $-38.00) - WATCH
DOGE/USDT-P: 9% WR (1/11 trades, $-25.00) - BLOCKED
```

---

#### HIB-005: LLM API Call Caching

**Problem**: LLM calls cost ~$0.01 each. Calling every cycle even when market hasn't changed wastes money.

**Solution**: Cache indicator calculations and skip LLM calls when market is calm.

**Implementation** (`hibachi_agent/data/hibachi_aggregator.py`):
```python
_indicator_cache: Dict[str, Dict] = {}  # symbol -> {indicators, timestamp, price_hash}
_cache_ttl_seconds = 60                 # 60-second TTL
_price_change_threshold = 0.001         # 0.1% price change invalidates

def _is_cache_valid(self, symbol, current_price):
    """Check if cached indicators still valid."""

def has_significant_change(self, market_data, threshold_pct=0.5):
    """Check if any market warrants LLM analysis."""
```

**Skip Logic**:
- Price moved < 0.1% → cache hit → no recalculation
- No cache misses AND no positions → skip LLM
- RSI extreme (<30 or >70) → always analyze

**Expected Cost Savings**:
- Current: ~$0.06/hour
- With caching: Skip ~50% of calls = ~$0.03/hour saved
- Monthly estimate: ~$22/month → ~$11/month (50% reduction)

---

#### HIB-006: Position Sizing Based on Conviction

**Problem**: All trades used same size regardless of LLM confidence.

**Caveat**: Per CLAUDE.md, high confidence doesn't correlate with actual win rate (0.9 conf = 51.7% actual WR). However, larger size on strong signals can still capture bigger moves when right.

**Implementation** (`hibachi_agent/bot_hibachi.py`):
```python
if raw_confidence >= 0.9:
    size_multiplier = 2.0    # $20 (2x base)
elif raw_confidence >= 0.8:
    size_multiplier = 1.5    # $15 (1.5x base)
else:
    size_multiplier = 1.0    # $10 (base)

# Hard cap: Never exceed 50% of available margin
```

**Expected Impact**: Capture larger moves on high-conviction signals while limiting risk.

---

#### HIB-007: Performance Dashboard

**Problem**: No consolidated view of Grid MM + LLM bot performance.

**Solution**: Created `scripts/hibachi_dashboard.py`

**Features**:
- Account Summary: Balance, open positions
- LLM Bot Stats: Wins/losses, win rate, P&L by symbol
- Grid MM Stats: Cycles, runtime, P&L
- Combined Daily: Total P&L from both strategies

**Usage**:
```bash
python3 scripts/hibachi_dashboard.py          # Run once
python3 scripts/hibachi_dashboard.py --watch  # Auto-refresh every 30s
```

---

**Summary of Hibachi Improvements**:

| Story | Feature | Expected Impact |
|-------|---------|-----------------|
| HIB-001 | Momentum confirmation | Fewer false signals |
| HIB-002 | Trailing stop | Lock in profits |
| HIB-003 | Tighter spreads | More fills |
| HIB-004 | Win rate tracking | Auto-block losers |
| HIB-005 | LLM caching | 50% cost reduction |
| HIB-006 | Conviction sizing | Capture bigger moves |
| HIB-007 | Dashboard | Performance visibility |

**Pending**: HIB-008 requires 24-hour live test to validate improvements.

