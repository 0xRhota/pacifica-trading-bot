# Strategy Tracker

**Last Updated**: 2025-11-03  
**Purpose**: Track all trading strategies (used, tested, and potential options)

---

## 📊 Active Strategies (Currently Deployed)

### Pacifica Bot - LLM-Driven Strategy
- **Status**: ✅ LIVE
- **Type**: LLM-based adaptive trading
- **Approach**: Context-aware decision making with full market data
- **Performance**: Tracked in live bot logs
- **Key Features**:
  - Uses Deep42 for macro context
  - Analyzes all markets simultaneously
  - Adaptive position sizing
  - Hourly deep research cycles

### Lighter Bot - RSI Oversold Long (Backtested)
- **Status**: 🚧 IMPLEMENTING
- **Type**: Rule-based, backtested
- **Strategy**: RSI Oversold Long
- **Backtest Performance** (90 days):
  - Return: **1.27%**
  - Win Rate: **66.3%**
  - Sharpe Ratio: 0.14 (low, but positive)
  - Total Trades: 39
  - Max Drawdown: 1.55%
- **Entry Rules**:
  - Buy when RSI < 30 (oversold)
- **Exit Rules**: (To be determined from backtest code)
- **Position Size**: $5-10 per trade (5-10% of $100 account)
- **Check Interval**: 60-90 seconds
- **Max Positions**: 3-5 concurrent

---

## 🧪 Backtested Strategies (Not Yet Deployed)

### Strategy: RSI Oversold Long ⭐ (BEST PERFORMER)
- **Status**: ✅ BACKTESTED
- **Backtest Period**: 90 days
- **Results**:
  - Return: **1.27%**
  - Win Rate: **66.3%**
  - Sharpe: 0.14
  - Trades: 39
  - Max Drawdown: 1.55%
- **Category**: Momentum
- **Deployment**: ✅ Implementing on Lighter bot
- **Strategy Code**:
  ```python
  # Buy when RSI < 30
  if current_rsi < 30:
      return "BUY"
  ```

### Strategy: Volume Spike Long (High Volume)
- **Status**: ✅ BACKTESTED
- **Backtest Period**: 90 days
- **Results**:
  - Return: 0.73%
  - Win Rate: 50.9%
  - Sharpe: 0.01 (near break-even)
  - Trades: **199** (high volume!)
  - Max Drawdown: Unknown
- **Category**: Volume-based
- **Strategy**: Buy when volume increases 50% and RSI < 45
- **Note**: High trade count but low Sharpe - may need refinement

---

## 💡 Potential Strategies (Not Yet Tested)

### Option 1: Mean Reversion Scalping (Theoretical)
- **Status**: 📋 PROPOSED
- **Type**: High-frequency scalping
- **Target**: High volume for airdrop farming
- **Approach**:
  - **Entry Signals**:
    1. RSI oversold (<30-35) + volume spike → LONG
    2. RSI overbought (>70) + volume spike → SHORT
    3. MACD crossover + RSI confirmation → Trade in crossover direction
    4. Bollinger Band touch + RSI extreme → Trade bounce/rejection
  - **Exit Rules**:
    - Take Profit: 0.3-0.5% gain
    - Stop Loss: 0.2-0.3% loss
    - Max Hold: 5-10 minutes (force exit if no profit)
    - Re-entry: Immediately after exit if signal still valid
  - **Position Size**: $5-10 per trade
  - **Trade Frequency**: 10-20 trades/day target
  - **Why This Works** (Theoretical):
    - Zero fees on Lighter make small profits viable
    - High frequency = many small wins
    - Mean reversion = RSI extremes tend to bounce
    - Volume confirmation = filters false signals
    - Tight stops = protects capital
- **Risk**: Not yet backtested - theoretical approach
- **Recommendation**: Test in paper trading first

### Option 2: Conservative RSI Long/Short
- **Status**: ✅ BACKTESTED (but failed threshold)
- **Backtest Results**:
  - Return: -0.22% to -0.01%
  - Win Rate: 44-55%
  - Trades: 40-101
  - Sharpe: -0.03 to 0.08
- **Strategy**: 
  - Long: RSI < 35 and price above SMA(50)
  - Short: RSI > 65 and price below SMA(50)
- **Note**: Tested but didn't meet profitability threshold

---

## 📈 Strategy Performance Summary

### Backtest Results (90 days, 4 symbols: SOL, ETH, BTC, PUMP)

| Strategy | Return | Win Rate | Sharpe | Trades | Status |
|----------|--------|----------|--------|--------|--------|
| **RSI Oversold Long** | **1.27%** | **66.3%** | 0.14 | 39 | ✅ Deploying |
| Volume Spike Long | 0.73% | 50.9% | 0.01 | 199 | ⚠️ Low Sharpe |
| Conservative RSI Long | -0.01% | 48.2% | 0.03 | 101 | ❌ Failed |
| Conservative RSI Short | -0.22% | 44.6% | -0.03 | 40 | ❌ Failed |
| RSI + MACD Long | -0.11% | 55.7% | 0.08 | 71 | ❌ Failed |

**Note**: 13 strategies "passed" but only RSI Oversold Long showed meaningful positive return.

---

## 🎯 Strategy Selection Criteria

### For High-Volume Airdrop Farming:
1. **Volume**: 100+ trades per 90 days (target)
2. **Return**: Positive (even 0.1%+ acceptable if volume is high)
3. **Sharpe**: Positive (prefer >0.5, but accept lower for volume)
4. **Win Rate**: >50% preferred

### For Profitability Focus:
1. **Return**: >1% per 90 days
2. **Sharpe**: >0.5 (prefer >1.0)
3. **Win Rate**: >55%
4. **Max Drawdown**: <5%

---

## 📝 Notes

- **Backtesting Limitations**: 
  - Historical data only
  - No slippage/fees simulation
  - Single symbol testing
  - No parameter optimization

- **Live Trading Differences**:
  - Real slippage
  - Real fees (0% on Lighter, 0.2% on Pacifica)
  - Market conditions change
  - Execution delays

- **Next Steps**:
  1. ✅ Deploy RSI Oversold Long on Lighter bot
  2. Monitor live performance
  3. Test Mean Reversion Scalping in paper trading
  4. Continue RBI agent backtesting for new strategies

---

## 🔄 Strategy Update Log

### 2025-11-03
- Created strategy tracker
- Documented RSI Oversold Long (1.27% return, 66% win rate)
- Added Mean Reversion Scalping as potential option
- Identified best backtested strategy for Lighter bot deployment

---

**Status**: Active tracking document - update as strategies are tested/deployed


