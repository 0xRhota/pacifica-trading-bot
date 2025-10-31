# High Sharpe Ratio & Volume Strategy for Airdrop Farming

**Date**: 2025-10-31  
**Goal**: Understand how to achieve high Sharpe ratios (15-34+) and high volume for airdrop points

---

## Leaderboard Analysis

### Top Performer Insights
- **Rank 1 (`arboooooooooor`)**:
  - Sharpe: **34.74** (highest)
  - Volume: **$24.9M** (highest)
  - Strategy: Extreme volume + consistent returns
  - Pattern: Many small trades, consistent profits

### Key Patterns

**High Sharpe Without High Volume**:
- Rank 2: Sharpe 19.12, Volume $37K (low volume, high Sharpe)
- Rank 5: Sharpe 15.48, Volume $32K, Account $1.56 (minimal capital!)
- **Insight**: High Sharpe is about **consistency**, not volume

**High Sharpe + High Volume**:
- Rank 1: Sharpe 34.74, Volume $24.9M
- Rank 3: Sharpe 17.27, Volume $5.8M
- **Insight**: Scale with consistent strategy

---

## What is Sharpe Ratio?

**Formula**: `Sharpe = (Average Return - Risk-Free Rate) / Standard Deviation of Returns`

**In Practice**:
- High Sharpe = Consistent, small wins with low volatility
- Low Sharpe = Erratic returns, big wins/losses

**Key Factors**:
1. **Consistency**: Many small profitable trades
2. **Low Volatility**: Minimize drawdowns, tight stop losses
3. **Win Rate**: Need >50% win rate ideally
4. **Risk/Reward**: Small losses, consistent small wins

---

## Strategies for High Sharpe Ratio

### 1. Market Making Strategy (Highest Sharpe)

**How it works**:
- Provide liquidity on both sides (bid/ask)
- Capture spread (buy low, sell high)
- Many small trades, consistent profits
- Low risk per trade

**Example**:
- Place bids at -0.1% below market
- Place asks at +0.1% above market
- Capture 0.2% spread on each round trip
- Many trades = high volume
- Small, consistent profits = high Sharpe

**Why it works**:
- Many trades (high volume)
- Small, consistent profits (high Sharpe)
- Low volatility (tight spreads)

### 2. Scalping Strategy

**How it works**:
- Enter/exit quickly (minutes to hours)
- Tight stop losses (0.5-1%)
- Small targets (0.5-2%)
- High frequency (many trades per day)

**Example**:
- Entry: Price breaks support/resistance
- Stop: 0.5% below entry
- Target: 1% above entry
- Win rate: 60-70%
- Many trades = high volume + high Sharpe

**Why it works**:
- Many trades (high volume)
- High win rate (high Sharpe)
- Small losses minimize volatility

### 3. Grid Trading Strategy

**How it works**:
- Place orders at multiple price levels
- Buy low, sell high automatically
- Many small trades across price range
- Captures volatility in both directions

**Example**:
- Place buy orders every 0.5% down
- Place sell orders every 0.5% up
- Price moves = automatic trades
- Consistent profits from volatility

**Why it works**:
- Many trades (high volume)
- Automatic execution (consistent)
- Works in sideways markets

---

## Why Your Bot Has Low Sharpe

### Current Issues

1. **Not Trading Enough**:
   - 96 decisions, 92 NOTHING (95.8%)
   - Only 4 trades total
   - Need 100+ trades for meaningful Sharpe

2. **Conservative Prompt**:
   - Current prompt says "wait for clear signals"
   - High Sharpe traders trade MORE, not less
   - Need to encourage action over inaction

3. **Large Position Sizes**:
   - $30 per trade = fewer trades
   - High Sharpe traders use smaller sizes ($10-20)
   - More trades = better Sharpe calculation

4. **Not Measuring Sharpe**:
   - Bot doesn't calculate Sharpe ratio
   - Can't optimize what you don't measure

---

## Strategies to Increase Volume & Sharpe

### Strategy 1: Market Making Bot (Highest Sharpe Potential)

**How to Implement**:
1. Place limit orders on both sides
2. Target 0.1-0.3% spread capture
3. Many small trades per day
4. Tight stop losses (0.5%)

**Prompt Changes**:
- Encourage placing limit orders
- Focus on spread capture
- Many small trades vs few large trades

### Strategy 2: Scalping Bot (High Volume)

**How to Implement**:
1. Trade on 1-5 minute timeframes
2. Tight stops (0.5-1%)
3. Quick targets (1-2%)
4. High frequency (every 1-5 minutes)

**Prompt Changes**:
- Encourage quick entries/exits
- Focus on short-term moves
- Accept smaller profits, more trades

### Strategy 3: Grid Trading Bot

**How to Implement**:
1. Place orders at multiple price levels
2. Buy low, sell high automatically
3. Many trades across price range
4. Works in sideways markets

**Prompt Changes**:
- Encourage placing multiple orders
- Focus on capturing volatility
- Accept many small trades

---

## Bot Modifications Needed

### 1. Add Sharpe Ratio Calculation

**New Module**: `llm_agent/utils/sharpe_calculator.py`

```python
def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from list of returns
    
    Args:
        returns: List of P&L percentages per trade
        risk_free_rate: Risk-free rate (default 0 for crypto)
    
    Returns:
        Sharpe ratio
    """
    if not returns:
        return 0.0
    
    avg_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return == 0:
        return 0.0
    
    sharpe = (avg_return - risk_free_rate) / std_return
    return sharpe
```

**Integration**:
- Add to `TradeTracker.get_stats()`
- Calculate from closed trades
- Log Sharpe ratio in stats

### 2. Volume-Focused Prompt Template

**New Template**: `llm_agent/prompts/volume_farming.md`

```markdown
# Trading Instructions - Volume Farming (High Sharpe Focus)

**Your Goal**: Generate high trading volume while maintaining consistent, small profits

**Strategy**: Market Making + Scalping
- Many small trades (10-20 per day)
- Tight stop losses (0.5-1%)
- Small profit targets (1-2%)
- High win rate (60%+)

**Key Principles**:
1. **Trade MORE, not less** - Volume is essential for airdrop points
2. **Small positions** - $10-20 per trade to enable more trades
3. **Quick exits** - Don't hold for days, exit when target hit
4. **Tight stops** - Minimize losses to maintain Sharpe ratio
5. **Spread capture** - Look for bid/ask spread opportunities

**Entry Signals**:
- Price breakouts (small moves)
- Orderbook imbalances (temporary)
- Momentum shifts (short-term)
- Volume spikes (immediate action)

**Exit Signals**:
- Target hit (1-2% profit)
- Stop loss hit (0.5-1%)
- Profit target reached (quick exit)
- Market reversal (tight stop)

**Risk Management**:
- Position size: $10-20 per trade (smaller = more trades)
- Stop loss: 0.5-1% (tight)
- Target: 1-2% (quick)
- Max positions: 5-10 (more concurrent trades)

**Volume Focus**:
- Prefer 10 small trades over 1 large trade
- Accept smaller profits for more trades
- Don't wait for perfect setups - act on small edges
- The goal is CONSISTENCY, not large wins

DECISION: [BUY <SYMBOL> | SELL <SYMBOL> | CLOSE <SYMBOL> | NOTHING]
REASON: [Your reasoning focusing on volume generation and Sharpe optimization]
```

### 3. Reduce Position Sizes

**Current**: $30 per trade  
**Recommended**: $10-20 per trade

**Why**:
- More trades possible with same capital
- Higher volume for airdrop points
- Better Sharpe calculation (more data points)
- Lower risk per trade

**Config Change**:
```python
# config.py
class PacificaConfig:
    MIN_POSITION_USD = 10.0  # Reduced from 30.0
    MAX_POSITION_USD = 20.0  # Reduced from 40.0
```

### 4. Increase Trading Frequency

**Current**: 5-minute intervals  
**Recommended**: 1-2 minute intervals

**Why**:
- More decisions = more trades
- Higher volume
- Better Sharpe with more data points

**Config Change**:
```python
# bot_llm.py
check_interval = 120  # 2 minutes instead of 300 (5 minutes)
```

### 5. Tighten Stop Losses

**Current**: 1% stop loss  
**Recommended**: 0.5% stop loss

**Why**:
- Minimize losses (higher Sharpe)
- Faster exits (more trades possible)
- Lower volatility

**Config Change**:
```python
# config.py
STOP_LOSS = 0.005  # 0.5% instead of 0.01 (1%)
```

### 6. Add Sharpe Ratio Tracking

**New Function**: `TradeTracker.calculate_sharpe_ratio()`

```python
def calculate_sharpe_ratio(self) -> float:
    """Calculate Sharpe ratio from closed trades"""
    closed = self.get_closed_trades()
    if len(closed) < 2:
        return 0.0
    
    returns = [t.get('pnl_pct', 0) for t in closed]
    avg_return = sum(returns) / len(returns)
    std_return = (sum((r - avg_return)**2 for r in returns) / len(returns))**0.5
    
    if std_return == 0:
        return 0.0
    
    sharpe = avg_return / std_return  # Risk-free rate = 0 for crypto
    return sharpe
```

---

## Recommended Bot Configuration for High Sharpe

### Volume Farming Bot Config

**File**: `llm_agent/bot_configs/volume_farming.json`

```json
{
  "bot_name": "volume_farming",
  "prompt_template": "volume_farming",
  "position_size": 15.0,
  "max_positions": 10,
  "check_interval": 120,
  "timeframe_focus": "swing",
  "log_file": "logs/volume_farming.log",
  "dry_run": false,
  "description": "High volume, high Sharpe ratio bot for airdrop farming"
}
```

### Prompt Template: Volume Farming

**Key Changes**:
- Encourage MORE trading (not less)
- Focus on small, consistent profits
- Tight stops, quick exits
- Accept smaller edge for more trades
- Goal: 10-20 trades per day

---

## Implementation Plan

### Phase 1: Add Sharpe Calculation
1. Create `llm_agent/utils/sharpe_calculator.py`
2. Add `calculate_sharpe_ratio()` to `TradeTracker`
3. Display Sharpe in `print_stats()`
4. Log Sharpe ratio in stats

### Phase 2: Create Volume Farming Prompt
1. Create `llm_agent/prompts/volume_farming.md`
2. Emphasize: Many trades, small profits, tight stops
3. Encourage action over inaction
4. Focus on spread capture and scalping

### Phase 3: Adjust Bot Configuration
1. Reduce position size: $30 → $15
2. Increase frequency: 5min → 2min
3. Tighten stops: 1% → 0.5%
4. Increase max positions: 3 → 10

### Phase 4: Test & Optimize
1. Run volume farming bot for 24 hours
2. Measure Sharpe ratio
3. Adjust prompt based on results
4. Iterate to improve Sharpe

---

## Expected Results

### Current Bot
- Decisions: 96 (mostly NOTHING)
- Trades: 4 total
- Volume: Low
- Sharpe: Unknown (not calculated)

### Volume Farming Bot (Target)
- Decisions: 720 per day (2-min intervals)
- Trades: 50-100 per day
- Volume: $750-1500 per day ($15 × 50-100 trades)
- Sharpe: 10-15+ (with consistent small wins)

### Market Making Bot (Ultimate Goal)
- Trades: 200+ per day
- Volume: $3000+ per day
- Sharpe: 20-30+ (with spread capture)

---

## Key Insights from Leaderboard

1. **Sharpe Ratio Formula**:
   - Consistency > Size
   - Many small wins > Few large wins
   - Low volatility > High volatility

2. **Volume Strategy**:
   - Top trader: $24.9M volume = Many trades
   - Many small positions = More trades
   - High frequency = More volume

3. **Risk Management**:
   - Tight stops minimize losses
   - Small positions reduce volatility
   - Consistent sizing improves Sharpe

4. **Trading Style**:
   - Market making (spread capture)
   - Scalping (quick entries/exits)
   - Grid trading (multiple levels)

---

## Action Items for Your Bot

1. ✅ **Add Sharpe ratio calculation** - Track performance
2. ✅ **Create volume farming prompt** - Encourage more trading
3. ✅ **Reduce position sizes** - Enable more trades
4. ✅ **Increase frequency** - More decisions = more trades
5. ✅ **Tighten stops** - Improve Sharpe with lower losses
6. ✅ **Add market making strategy** - Highest Sharpe potential

---

## Next Steps

1. Review this strategy document
2. Implement Sharpe ratio calculation
3. Create volume farming prompt template
4. Adjust bot configuration
5. Test with small capital
6. Monitor Sharpe ratio improvement
7. Scale up when Sharpe > 10

**Goal**: Achieve Sharpe ratio > 15 with volume > $50K/week for airdrop farming.

---

**End of Strategy Document**

