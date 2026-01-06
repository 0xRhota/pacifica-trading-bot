# Contributing to Hopium Agents

This guide is for colleagues who want to understand, modify, or extend the codebase.

## Getting Started

### Prerequisites
- Python 3.9+ (Extended agent requires 3.11+)
- pip
- API keys for exchanges you want to trade on
- OpenRouter API key for LLM access

### Setup

```bash
# Clone the repo
git clone https://github.com/[your-username]/hopium-agents.git
cd hopium-agents

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Verify Installation

```bash
# Test LLM connection
python3 -c "
from llm_agent.llm.model_client import ModelClient
client = ModelClient()
print(client.query('Say hello'))
"

# Test exchange connection (hibachi example)
python3 -c "
from dexes.hibachi.hibachi_sdk import HibachiSDK
sdk = HibachiSDK()
print(sdk.get_account_info())
"
```

## Project Architecture

### Core Components

```
llm_agent/                  # The brain - shared by all agents
├── llm/
│   ├── model_client.py     # LLM API wrapper
│   └── prompt_formatter.py # Builds prompts from market data
├── data/
│   ├── aggregator.py       # Fetches market data
│   └── indicators.py       # Technical indicators
└── self_learning.py        # Tracks performance, blocks poor symbols
```

### Exchange Agents

Each exchange has its own agent that uses the shared `llm_agent/`:

```
hibachi_agent/
├── bot_hibachi.py          # Main entry point
├── data/                   # Hibachi-specific data fetching
└── execution/              # Order execution logic

lighter_agent/              # Same structure
extended_agent/             # Same structure
paradex_agent/              # Grid MM specific
```

### Adding a New Exchange

1. Create new directory: `new_exchange_agent/`
2. Implement data fetcher in `data/` (fetch OHLCV, positions)
3. Implement executor in `execution/` (place orders)
4. Create `bot_new_exchange.py` entry point
5. Add SDK wrapper to `dexes/new_exchange/`

Use existing agents as templates. The key interfaces:
- `get_positions()` - Returns current positions
- `get_market_data(symbol)` - Returns OHLCV + indicators
- `place_order(symbol, side, size)` - Executes trade
- `close_position(symbol)` - Closes position

## Development Workflow

### Running an Agent (Development Mode)

```bash
# Dry run (no real trades)
python3 -m hibachi_agent.bot_hibachi --dry-run --interval 60

# Live trading
python3 -m hibachi_agent.bot_hibachi --live --interval 600
```

### Testing Changes

1. Run in dry-run mode first
2. Check logs for expected behavior
3. Test with small positions
4. Monitor for 24+ hours before full deployment

### Code Style

- Use type hints for public functions
- Docstrings on classes and public methods
- Keep functions focused and small
- Log important decisions and errors

### Commit Messages

```
feat: Add new indicator (Bollinger Bands)
fix: Handle API timeout in lighter_agent
docs: Update strategy documentation
refactor: Simplify position sizing logic
```

## Key Files to Understand

| File | Purpose |
|------|---------|
| `llm_agent/llm/prompt_formatter.py` | How prompts are built |
| `llm_agent/prompts_archive/v9_qwen_enhanced.txt` | The winning strategy |
| `logs/strategy_switches.log` | Strategy evolution history |
| `MASTER_ANALYSIS.md` | Performance data and insights |

## Strategy Development

### The Prompt IS the Strategy

The LLM prompt defines the trading strategy. To modify strategy:

1. Edit `llm_agent/llm/prompt_formatter.py`
2. Or create new prompt file in `llm_agent/prompts_archive/`
3. Test in dry-run mode
4. Log the strategy switch in `logs/strategy_switches.log`

### What Works (From Our Data)

- **5-signal scoring** (RSI, MACD, Volume, Price Action, OI)
- **Asymmetric R:R** (3:1 minimum)
- **Hard exit rules** (+2%/-1.5%, 2h min hold)
- **Quality over quantity** (2-5 positions max)
- **SHORT bias** on Lighter/Extended

### What Doesn't Work

- Deep42 for exit decisions (causes panic exits)
- High confidence = larger size (0.8 conf = 44% actual WR)
- Time-based Grid refresh (use price move trigger)
- BCH, BNB, ZEC trading (consistent losers)

## Debugging

### Common Issues

**LLM returns invalid format:**
- Check prompt formatting
- Add retry logic with clearer instructions
- Default to NO_TRADE on parse errors

**Order rejected:**
- Check min notional ($10 on Paradex)
- Verify sufficient balance
- Check position limits

**Data stale:**
- Check API connectivity
- Verify timestamps
- Add staleness checks

### Log Analysis

```bash
# Check recent errors
grep -i error logs/hibachi_bot.log | tail -20

# Check decisions
grep "DECISION:" logs/hibachi_bot.log | tail -20

# Check P&L
grep "pnl" logs/trades/hibachi.json | tail -20
```

## Git Practices

### What to Commit
- Source code (.py)
- Documentation (.md)
- Configuration templates (.env.example)
- Requirements (requirements.txt)

### What NOT to Commit
- `.env` (secrets)
- `logs/` (trade data)
- `__pycache__/`
- IDE files

### Branching

```bash
# Feature branch
git checkout -b feat/new-indicator

# Make changes, test
# ...

# Commit and push
git add .
git commit -m "feat: Add Bollinger Bands indicator"
git push origin feat/new-indicator
```

## Questions?

- Check [MASTER_ANALYSIS.md](MASTER_ANALYSIS.md) for data insights
- Check [CLAUDE.md](CLAUDE.md) for AI agent guidelines
- Check `logs/strategy_switches.log` for strategy history
- Ask the codebase owner for clarification
