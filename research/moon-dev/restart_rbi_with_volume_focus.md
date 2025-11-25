# Restart RBI Agent with Volume-Focused Strategies

## What We Changed

1. **Updated `ideas.txt`** with 15 new volume-focused strategies
   - Focus: Scalping, mean reversion, high frequency
   - Goal: 100+ trades, match buy-and-hold returns

2. **Created volume-focused prompts** (ready to integrate)
   - Emphasizes trade frequency
   - Small profit targets (0.3-0.5%)
   - Tight stops (0.2-0.3%)

## Next Steps

To restart RBI agent with new volume-focused strategies:

```bash
cd /Users/admin/Documents/Projects/pacifica-trading-bot/moon-dev-reference
python3 src/agents/rbi_agent_pp_multi.py
```

The agent will:
1. Read new strategies from `ideas.txt`
2. Generate backtest code for each
3. Test on SOL and ETH data (90 days, 15m)
4. Find strategies that:
   - Generate 100+ trades
   - Return > 5% (ETH) or > 15% (SOL)
   - Positive Sharpe ratio

## Success Criteria

✅ **PASSING Strategy**:
- Return > 5% (ETH) or > 15% (SOL) over 90 days
- 100+ trades generated
- Sharpe ratio > 0.5
- Win rate > 40%

## Current Status

- **15 new volume-focused strategies** in `ideas.txt`
- **Previous 10 strategies**: All failed (best was -0.61%)
- **Ready to restart**: New strategies focus on volume + profitability


