# RBI Agent - File Index & Documentation Map

**Status**: MVP Complete ✅  
**Date**: 2025-11-01  
**Purpose**: Reference guide for all RBI agent files and documentation

---

## Core Implementation Files

### `rbi_agent/rbi_agent.py`
**Status**: ✅ ACTIVE  
**Purpose**: Main RBI agent implementation  
**Classes**:
- `RBIAgent` - Strategy discovery and testing coordinator
- `StrategyBacktester` - Backtesting engine

**Key Methods**:
- `RBIAgent.test_strategy()` - Main entry point for testing strategies
- `RBIAgent.generate_backtest_code()` - LLM code generation
- `StrategyBacktester.execute_strategy()` - Execute backtest on historical data
- `StrategyBacktester.fetch_historical_data()` - Fetch OHLCV from Pacifica

**Dependencies** (Read-Only):
- `llm_agent/data/pacifica_fetcher.py` - Historical data fetching
- `llm_agent/data/indicator_calculator.py` - Technical indicators
- `llm_agent/llm/model_client.py` - LLM API client

**Safety**: ✅ Does NOT modify any live bot code

---

## Documentation Files

### `rbi_agent/README.md`
**Status**: ✅ ACTIVE  
**Purpose**: Complete documentation  
**Contents**:
- Overview and architecture
- Usage examples
- Integration options
- Limitations and future enhancements
- Safety guarantees

### `rbi_agent/EXAMPLES.md`
**Status**: ✅ ACTIVE  
**Purpose**: Usage examples and integration patterns  
**Contents**:
- Command line usage
- Python API examples
- Batch testing examples
- Integration with main bot

### `rbi_agent/QUICK_REFERENCE.md`
**Status**: ✅ ACTIVE  
**Purpose**: Quick reference guide  
**Contents**:
- Quick start commands
- What it does (4-step process)
- Example output
- Integration options

### `rbi_agent/__init__.py`
**Status**: ✅ ACTIVE  
**Purpose**: Package initialization  
**Version**: 0.1.0

---

## Related Documentation

### `AGENTS.md` (Project Root)
**Status**: ✅ ACTIVE  
**Purpose**: AI agent collaboration guide  
**Contents**:
- Agent roles and capabilities
- Repository organization rules
- Common workflows
- Safety guidelines

### `research/moon-dev/NEW_INSIGHTS_ANALYSIS.md`
**Status**: ✅ ACTIVE  
**Purpose**: Moon Dev RBI agent analysis  
**Contents**:
- Moon Dev's RBI agent concept
- How it works
- How we adapted it
- Key insights

### `PROGRESS.md` (Project Root)
**Status**: ✅ ACTIVE  
**Section**: 2025-11-01 - RBI Agent MVP Implemented  
**Contents**: Implementation summary, files created, usage

### `REPOSITORY_STRUCTURE.md` (Project Root)
**Status**: ✅ ACTIVE  
**Section**: `/rbi_agent/` - Research-Based Inference Agent  
**Contents**: File listing, key features, usage, safety

---

## External References

### Moon Dev Repository
- **URL**: https://github.com/moondevonyt/moon-dev-ai-agents
- **Inspiration**: RBI (Research-Based Inference) Agent
- **Concept**: Automated strategy discovery via LLM code generation

### Backtesting.py Library
- **URL**: https://kernc.github.io/backtesting.py/
- **Note**: Moon Dev uses this library, we built custom backtester

### Pacifica API
- **Docs**: https://docs.pacifica.fi/
- **Endpoints Used**: `/kline` (OHLCV candles)
- **Data Source**: Historical market data for backtesting

---

## File Relationships

```
rbi_agent/
├── rbi_agent.py          # Main implementation
│   ├── RBIAgent          # Uses ModelClient, StrategyBacktester
│   └── StrategyBacktester # Uses PacificaDataFetcher, IndicatorCalculator
├── README.md             # Full documentation
├── EXAMPLES.md           # Usage examples
├── QUICK_REFERENCE.md    # Quick reference
└── __init__.py          # Package init

Dependencies (Read-Only):
├── llm_agent/data/pacifica_fetcher.py
├── llm_agent/data/indicator_calculator.py
└── llm_agent/llm/model_client.py

Documentation References:
├── AGENTS.md (project root)
├── PROGRESS.md (project root)
├── REPOSITORY_STRUCTURE.md (project root)
└── research/moon-dev/NEW_INSIGHTS_ANALYSIS.md
```

---

## Usage Patterns

### Command Line
```bash
python -m rbi_agent.rbi_agent \
    --strategy "Buy when RSI < 30" \
    --symbols SOL ETH BTC \
    --days 30
```

### Python API
```python
from rbi_agent.rbi_agent import RBIAgent

agent = RBIAgent()
result = agent.test_strategy("Buy when RSI < 30")
```

### Batch Testing
```python
strategies = ["Strategy 1", "Strategy 2", "Strategy 3"]
results = [agent.test_strategy(s) for s in strategies]
```

---

## Safety Guarantees

✅ **Read-Only Access**: Only reads from data fetchers, never modifies  
✅ **Isolated**: Completely separate from `llm_agent/` directory  
✅ **No Live Trading**: Pure backtesting, no real trades  
✅ **No Code Modification**: Generates code in memory, doesn't save  

---

## Integration Points (Future)

### Current: Standalone Tool
- Manual execution
- Manual review of results
- Manual integration into prompts

### Future Options:
1. **Auto-Discovery Mode**: Weekly automated runs
2. **Strategy Storage**: Save passing strategies to JSON
3. **Prompt Integration**: Auto-add proven strategies to bot prompt
4. **Paper Trading**: Test new strategies in paper trading mode first

---

**Last Updated**: 2025-11-01  
**Maintained By**: Composer (Claude Sonnet via Cursor)

