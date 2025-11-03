# RBI Agent - Usage Examples

This directory contains examples and documentation for the RBI (Research-Based Inference) Agent.

## Quick Start

```bash
# Test a simple strategy
python -m rbi_agent.rbi_agent \
    --strategy "Buy when RSI < 30" \
    --symbols SOL ETH BTC \
    --days 30

# Test with custom thresholds
python -m rbi_agent.rbi_agent \
    --strategy "Buy when RSI < 35 and volume spike > 50%" \
    --symbols SOL ETH \
    --days 60 \
    --min-return 2.0
```

## Example Strategies

### Momentum Strategies
- "Buy when RSI < 30 and volume increases 30%"
- "Sell when RSI > 70 and funding rate > 0.1%"
- "Buy when price crosses SMA(20) from below with high volume"

### Mean Reversion Strategies
- "Buy when price drops below Bollinger Band lower and RSI < 35"
- "Sell when price rises above Bollinger Band upper and RSI > 65"

### Funding Rate Strategies
- "Buy when funding rate < -0.05% (shorts paying longs)"
- "Sell when funding rate > 0.15% (longs paying shorts)"

### Multi-Condition Strategies
- "Buy when RSI < 40 AND volume > 1.5x average AND MACD crosses above signal"
- "Sell when RSI > 70 AND funding rate > 0.1% AND price above SMA(50)"

## Python API Examples

### Basic Test

```python
from rbi_agent.rbi_agent import RBIAgent

agent = RBIAgent()

result = agent.test_strategy(
    strategy_description="Buy when RSI < 30",
    symbols=["SOL", "ETH", "BTC"],
    days_back=30
)

print(f"Passed: {result['passed']}")
print(f"Return: {result['return_pct']:.2f}%")
print(f"Win Rate: {result['win_rate']:.1%}")
```

### Batch Testing

```python
from rbi_agent.rbi_agent import RBIAgent

agent = RBIAgent()

strategies = [
    "Buy when RSI < 30",
    "Buy when RSI < 35 and volume increases 30%",
    "Sell when RSI > 70"
]

results = []
for strategy in strategies:
    result = agent.test_strategy(strategy)
    results.append(result)
    print(f"{strategy}: {'✅' if result['passed'] else '❌'} "
          f"{result['return_pct']:.2f}% return")

# Sort by return
results.sort(key=lambda x: x['return_pct'], reverse=True)
print(f"\nBest strategy: {results[0]['strategy_description']}")
```

### Custom Thresholds

```python
from rbi_agent.rbi_agent import RBIAgent

agent = RBIAgent()

result = agent.test_strategy(
    strategy_description="Buy when RSI < 30",
    symbols=["SOL", "ETH", "BTC"],
    days_back=60,
    min_return=2.0,      # Minimum 2% return
    min_win_rate=0.45,   # Minimum 45% win rate
    min_sharpe=0.7       # Minimum Sharpe ratio 0.7
)
```

## Integration with Main Bot

### Option 1: Manual Review

```python
from rbi_agent.rbi_agent import RBIAgent

# Discover strategies
agent = RBIAgent()
result = agent.test_strategy("Buy when RSI < 30")

if result['passed']:
    # Review results manually
    print(f"Strategy passed: {result['return_pct']:.2f}%")
    print(f"Generated code:\n{result['strategy_code']}")
    # Manually add to prompt or strategy file
```

### Option 2: Save Results

```python
import json
from rbi_agent.rbi_agent import RBIAgent

agent = RBIAgent()

strategies = [
    "Buy when RSI < 30",
    "Sell when RSI > 70"
]

passed_strategies = []
for strategy in strategies:
    result = agent.test_strategy(strategy)
    if result['passed']:
        passed_strategies.append({
            'description': result['strategy_description'],
            'code': result['strategy_code'],
            'return': result['return_pct'],
            'win_rate': result['win_rate']
        })

# Save to file
with open('rbi_agent/proven_strategies.json', 'w') as f:
    json.dump(passed_strategies, f, indent=2)
```

---

## Troubleshooting

### No Data Returned
- Check symbol is valid Pacifica symbol
- Verify API connectivity
- Check date range (may not have enough historical data)

### Strategy Code Generation Fails
- Check DeepSeek API key is set
- Verify strategy description is clear
- Try simpler strategy descriptions

### All Strategies Fail
- Lower thresholds (`min_return`, `min_win_rate`)
- Increase `days_back` for more data
- Try different symbols

---

## Next Steps

1. Test various strategies to find what works
2. Save passing strategies to `proven_strategies.json`
3. Integrate proven strategies into main bot prompt
4. Run weekly to discover new patterns

See `README.md` for full documentation.

