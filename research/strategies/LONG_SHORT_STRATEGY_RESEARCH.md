# Long/Short Strategy Research

**Date**: 2025-10-07
**Goal**: Implement intelligent long/short decisions in trading strategy

---

## Data Sources Available

### 1. Pacifica Market Data (Always Available)
**Location**: `pacifica_bot.py` / `dexes/pacifica/pacifica_sdk.py`

**What we get**:
- Current market price
- Orderbook depth (bids and asks)
- Recent trades
- Account balance and equity

**Useful for directional bias**:
- **Orderbook imbalance**: If bid volume >> ask volume → bullish signal
- **Spread analysis**: Tight spreads = strong market, wide spreads = weak
- **Price momentum**: Recent price movement direction

### 2. Cambrian Blockchain Data (Available via API)
**Location**: `research/cambrian/cambrian_client.py`

**What we get**:
- Buy/sell trade counts and volumes (24h)
- Buy-to-sell ratio (key indicator!)
- OHLCV data (historical prices)
- Trending tokens
- Trader leaderboard
- Token security metrics

**Useful for directional bias**:
- **Buy/sell ratio > 1.1**: More buying pressure → bullish signal
- **Buy/sell ratio < 0.9**: More selling pressure → bearish signal
- **Volume trends**: Increasing volume confirms moves
- **Smart money**: Leaderboard shows what winners are doing

### 3. Cambrian via MCP Tools (Available Now!)
**Available MCP Tools**:
- `mcp__cambrian-clickhouse__*` - Direct ClickHouse queries
- `mcp__cambrian-knowledge-base__*` - Knowledge base queries

**What we can query**:
- Liquidity pool data
- Token holder analysis
- Large transfer tracking
- Fee distribution
- Real-time on-chain metrics

---

## Recommended Approach for Long/Short Logic

### Phase 1: Simple Momentum-Based (Quick to implement)

Use Cambrian buy/sell ratio as primary signal:

```python
def _analyze_market_direction(self, symbol: str, current_price: float, orderbook: dict) -> Optional[str]:
    # 1. Get Cambrian buy/sell ratio
    cambrian = CambrianClient()
    signal = cambrian.get_momentum_signal(symbol)

    buy_sell_ratio = signal.get('buy_to_sell_ratio')

    # 2. Make decision
    if buy_sell_ratio is None:
        return None  # No data, skip trade

    if buy_sell_ratio > 1.2:
        return "bid"   # Strong buying pressure → go long
    elif buy_sell_ratio < 0.8:
        return "ask"   # Strong selling pressure → go short
    else:
        return None    # Neutral, skip trade
```

**Pros**: Simple, reliable data source, proven indicator
**Cons**: Only uses one signal, may lag market

### Phase 2: Multi-Signal Confirmation (More robust)

Combine multiple signals for higher confidence:

```python
def _analyze_market_direction(self, symbol: str, current_price: float, orderbook: dict) -> Optional[str]:
    signals = []

    # Signal 1: Cambrian buy/sell ratio
    cambrian = CambrianClient()
    momentum = cambrian.get_momentum_signal(symbol)
    buy_sell_ratio = momentum.get('buy_to_sell_ratio', 1.0)

    if buy_sell_ratio > 1.1:
        signals.append("long")
    elif buy_sell_ratio < 0.9:
        signals.append("short")

    # Signal 2: Orderbook imbalance
    bid_depth = sum(float(b[1]) for b in orderbook.get('bids', [])[:10])
    ask_depth = sum(float(a[1]) for a in orderbook.get('asks', [])[:10])

    if bid_depth > ask_depth * 1.2:
        signals.append("long")
    elif ask_depth > bid_depth * 1.2:
        signals.append("short")

    # Signal 3: Recent price momentum (if available)
    # TODO: Track recent price changes

    # Decision: Need 2+ signals in same direction
    long_votes = signals.count("long")
    short_votes = signals.count("short")

    if long_votes >= 2:
        return "bid"
    elif short_votes >= 2:
        return "ask"
    else:
        return None  # Not enough conviction
```

**Pros**: More reliable, reduces false signals
**Cons**: May miss some opportunities, more complex

### Phase 3: ML-Based (Future)

Use Cambrian ClickHouse data to build ML model:
- Historical price movements
- On-chain metrics
- Liquidity patterns
- Smart money activity

**Implementation**: Later when we have more data and confidence

---

## Implementation Steps

### Step 1: Add Cambrian to Strategy
```bash
# Already have cambrian_client.py, just need to import it
```

### Step 2: Update long_short.py
Add Cambrian client initialization and momentum signal logic

### Step 3: Test with Paper Trading First
- Run strategy with small test positions
- Log all signals and outcomes
- Verify logic before scaling

### Step 4: Gradual Rollout
- Start with same position sizes as long-only ($10-20)
- Monitor win rate and P&L
- Adjust thresholds based on results

---

## Risk Considerations

### Shorts are Riskier
- Long max loss = 100% (price → $0)
- Short max loss = unlimited (price → ∞)
- Solution: Keep same tight stop-loss (10%)

### Funding Rates
- Perps have funding rates (longs pay shorts or vice versa)
- Check if Pacifica provides funding rate data
- Consider funding when holding positions longer

### Market Conditions
- Current market is "a little bit red" (user's words)
- Shorts may be more profitable today
- Strategy should adapt to conditions automatically

---

## Success Metrics

Track separately for longs vs shorts:
- Win rate (target: >40%)
- Average P&L per trade
- Total P&L
- Max drawdown
- Time to profit

Compare with basic long-only strategy to validate improvement.

---

## Quick Start Plan

**Today (Next 30 minutes)**:
1. Import Cambrian client into long_short.py
2. Implement Phase 1 (simple momentum)
3. Test with single token (SOL)
4. Verify signals make sense

**This week**:
1. Run alongside basic strategy with small positions
2. Collect data on signal accuracy
3. Iterate on thresholds (1.2/0.8 vs 1.1/0.9)
4. Add multi-signal confirmation (Phase 2)

**Next steps**:
1. Expand to all tokens (BTC, ETH, PENGU, XPL, ASTER)
2. Add orderbook imbalance signal
3. Track performance vs long-only
4. Consider Cambrian MCP tools for deeper analysis

---

## Files to Modify

1. ✅ `strategies/long_short.py` - Add Cambrian logic
2. ✅ `strategies/README.md` - Update status
3. ⏳ `live_bot.py` - Already supports strategy switching
4. ⏳ `.env` - Verify CAMBRIAN_API_KEY exists

---

## Notes

- User wants to "make some intelligent decisions about whether to open a long or a short"
- Today markets are "a little bit red" - good day to test shorts
- Keep basic long-only strategy intact for fallback
- Easy switching between strategies is key requirement

**Ready to implement Phase 1 when you're ready!**
