# High-Volume Trading Strategy Goal

## Objective
Find strategies that:
1. **Match or exceed buy-and-hold returns**
   - SOL: +15.37% (90 days)
   - ETH: +5.56% (90 days)
2. **Generate massive trading volume** (for airdrop farming)
   - Minimum 100+ trades per 90 days
   - Ideally 200+ trades
3. **Positive Sharpe ratio** (risk-adjusted returns)
   - Target: Sharpe > 1.0
   - Minimum: Sharpe > 0.5

## Strategy Characteristics Needed

### Volume Generation
- **High frequency**: Many small trades
- **Quick exits**: 0.3-0.5% profit targets (scalping)
- **Tight stops**: 0.2-0.3% to limit losses
- **Re-enter frequently**: Don't wait for perfect setups

### Profitability Requirements
- Must beat buy-and-hold on returns
- Win rate > 50% (or very large sample size)
- Average trade profit > average trade loss

## Strategy Types to Test

1. **Mean Reversion Scalping**
   - Trades every oversold bounce
   - Quick 0.3-0.5% profits
   - High frequency

2. **Volume-Weighted Scalping**
   - Enters on volume spikes
   - Exits quickly for profit
   - Many trades per day

3. **Range Trading**
   - Trades within Bollinger Bands
   - Multiple entries/exits
   - Consistent volume

4. **Quick Reversal**
   - Catches micro reversals
   - Very small profit targets
   - Maximum frequency

## Current Status

**All 10 tested strategies FAILED:**
- Best: -0.61% return (T04_AdaptiveOversold)
- Worst: -25.81% return (T00_MomentumContraction)
- None match buy-and-hold

**New Ideas Generated:**
- 15 volume-focused strategies in `ideas.txt`
- Focus on scalping, mean reversion, high frequency
- Target: Many small profitable trades

## Next Steps

1. Run RBI agent on new volume-focused strategies
2. Monitor for strategies that:
   - Trade 100+ times in 90 days
   - Return > 5% (ETH) or > 15% (SOL)
   - Sharpe > 0.5
3. Deploy winning strategies to live bot
4. Monitor volume generation on exchange


