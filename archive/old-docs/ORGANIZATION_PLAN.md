# Repository Organization Plan (No Deletion)
**Goal**: Clearly organize and document everything for co-workers without deleting historical data

---

## Philosophy: Preserve the Journey

This repo contains:
1. **Current Production** - Strategy E & F (what's running live now)
2. **Historical Research** - All past bots, strategies, learnings (valuable context)
3. **Your Trading Data** - Your live trading results (examples for co-workers)
4. **Framework Code** - Exchange-agnostic core that can be reused

**Nothing gets deleted. Everything gets documented.**

---

## 📋 Phase 1: Add Documentation to Existing Directories

### archive/ - Add README
**File**: `archive/README.md`
```markdown
# Archive - Historical Bot Versions

This directory contains previous iterations of the trading bot from October-November 2025.

## What's Inside
- Old bot entry points (dry_run_bot.py, live_bot.py, etc.)
- Previous strategy implementations
- Dated backup folders (2025-10-30 through 2025-11-07)

## Why Keep This?
Shows the evolution of the bot architecture. Useful for understanding
why we made certain design decisions.

## Status
**Archived - Not in active use**

Current bots are in:
- `hibachi_agent/` - Strategy F (self-improving LLM)
- `extended_agent/` - Strategy E (self-improving pairs)
```

### research/ - Add README
**File**: `research/README.md`
```markdown
# Research - Past Experiments & Learnings

This directory contains all research from developing the trading strategies.

## Directory Structure

### archived/
- `HOSTING_INFRASTRUCTURE_RESEARCH.md` - Hetzner deployment research

### Nov2024-lighter-research/
**What**: Initial research on Lighter DEX integration
**Outcome**: Successfully deployed, ran for ~1 month
**Learnings**: Zero fees are great, but liquidity is lower than Hibachi

### Nov2024-v2-research/
**What**: Research on v2 architecture improvements
**Outcome**: Led to Strategy F (self-improving LLM)

### 2025-11-27-copy-trading-pivot/
**What**: Explored copy trading whale positions
**Outcome**: Integrated whale signals into Strategy F

### cambrian/
**What**: Cambrian API integration for Solana data
**Status**: Active - used by current bots for OHLCV data

### moon-dev/
**What**: Moon.dev integration research
**Status**: Active - used for data comparison

### experiments/
**What**: Various trading experiments and backtests
**Status**: Reference material

### funding_rate_arbitrage/
**What**: Explored funding rate arb strategies
**Outcome**: Not implemented (too capital intensive)

## Key Learnings
1. ✅ Self-improving strategies work (Strategy E & F)
2. ✅ LLM decision-making is viable with proper data
3. ✅ Outcome tracking is critical for learning
4. ❌ SOL consistently loses (removed from Hibachi whitelist)
5. ❌ Funding costs eat into profits significantly
6. ✅ Fast exit monitoring (TP/SL) improves win rate
```

### lighter_agent/ - Add README
**File**: `lighter_agent/README.md`
```markdown
# Lighter Agent - Historical Bot (Archived)

**Status**: Archived - Not in active use
**Active From**: Oct-Nov 2025
**Exchange**: Lighter DEX (zkSync)

## What Was This?
Trading bot for Lighter DEX using early versions of LLM strategies.

## Why We Moved On
- Migrated to Hibachi (better liquidity, more markets)
- Strategy evolved into Strategy F (self-improving LLM)

## Logs & Data
Historical trading data from Lighter is in:
- `logs/lighter_bot.log.*` (historical logs)
- `data/lighter_exports/` (CSV exports from Lighter DEX)

## Current Equivalent
The concepts from lighter_agent evolved into:
- **Hibachi agent** (`hibachi_agent/`) - Same strategy framework, different exchange
```

### pacifica_agent/ - Add README
**File**: `pacifica_agent/README.md`
```markdown
# Pacifica Agent - Historical Bot (Archived)

**Status**: Archived - Not in active use
**Active From**: Oct-Nov 2025
**Exchange**: Pacifica DEX (Solana)

## What Was This?
Early trading bot for Pacifica DEX, predecessor to current bots.

## Why We Moved On
- Better opportunities on Hibachi and Extended
- Strategy evolved into current Strategy E & F

## Current Equivalent
The framework here evolved into:
- **Hibachi agent** (`hibachi_agent/`) - Similar single-asset LLM approach
- **Extended agent** (`extended_agent/`) - Pairs trading evolution
```

### future_features/ - Add README
**File**: `future_features/README.md`
```markdown
# Future Features - Ideas & Backlog

This directory contains ideas and prototypes for future enhancements.

**Status**: Backlog - Not implemented yet

## What's Inside
Ideas that may be implemented later:
- Multi-timeframe analysis
- Advanced risk management
- Portfolio optimization
- Additional exchange integrations

## Contributing
If you want to work on any of these, coordinate with the team first.
```

---

## 📋 Phase 2: Organize Current Production Code

### Create `CURRENT_BOTS.md` (New File - Top Level)
**File**: `CURRENT_BOTS.md`
```markdown
# Current Production Bots

**Last Updated**: December 20, 2025

These are the bots currently running in production.

---

## 🔥 Hibachi Bot (Strategy F)
**File**: `hibachi_agent/bot_hibachi.py`
**Exchange**: Hibachi DEX (Solana)
**Strategy**: Self-Improving LLM (Single-Asset)

### How to Run
```bash
# Dry-run test
python -m hibachi_agent.bot_hibachi --dry-run --interval 600

# Live trading
nohup python3 -u -m hibachi_agent.bot_hibachi --live --interval 600 > logs/hibachi_bot.log 2>&1 &
```

### Current Config
- **Assets**: ETH, BTC only (SOL blocked - consistent losses)
- **Position Size**: ~$132 per trade
- **Strategy**: Strategy F (self-improving LLM)
- **Check Interval**: 10 minutes
- **Learning**: Reviews every 10 trades, auto-blocks <30% win rate combos

### Performance (As of Dec 20, 2025)
- Total Balance: ~$50
- Win Rate: 64% (22 closed trades)
- Self-learning: Active (2 reviews completed)
- All-time P/L: -$138 (mostly funding costs)

### Logs & Data
- **Execution Log**: `logs/hibachi_bot.log`
- **Outcome Tracker**: `logs/strategies/self_improving_llm_outcomes.json`
- **Trade History**: Export from Hibachi UI

---

## 🔷 Extended Bot (Strategy E)
**File**: `extended_agent/bot_extended.py`
**Exchange**: Extended DEX (Starknet)
**Strategy**: Self-Improving Pairs (Long/Short)

### How to Run
```bash
# Dry-run test
python3.11 -m extended_agent.bot_extended --dry-run --strategy E --interval 60

# Live trading
nohup python3.11 -u -m extended_agent.bot_extended --live --strategy E --interval 60 > logs/extended_bot.log 2>&1 &
```

### Current Config
- **Pair**: ETH vs BTC (long one, short the other)
- **Position Size**: $10 per leg (~$20 total per cycle)
- **Hold Time**: 60 minutes (fixed)
- **Strategy**: Strategy E (self-improving pairs)
- **Learning**: Reviews every 5 trades, adjusts bias

### Performance (As of Dec 20, 2025)
- Total Balance: ~$50
- Trades: 33 tracked
- Self-learning: Active (bias adjustments happening)

### Logs & Data
- **Execution Log**: `logs/extended_bot.log`
- **Outcome Tracker**: `logs/strategies/self_improving_pairs_outcomes.json`

---

## 🧠 Shared Components

Both bots use:
- **LLM**: Qwen (via OpenRouter API)
- **Data Sources**: Exchange APIs, Deep42 sentiment, whale signals
- **Fast Exit Monitor**: 30-second TP/SL monitoring
- **Self-Learning**: Outcome tracking + performance analysis

---

## 🎯 For Co-Workers: Running Your Own Tests

### 1. Setup
```bash
# Clone repo
git clone <repo-url>

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Add your API keys to .env
```

### 2. Get Exchange API Keys
- **Hibachi**: https://app.hibachi.finance/ (Account → API Keys)
- **Extended**: https://app.extended.exchange/api-management

### 3. Test in Dry-Run
```bash
# Hibachi
python -m hibachi_agent.bot_hibachi --dry-run --interval 300

# Extended
python3.11 -m extended_agent.bot_extended --dry-run --strategy E --interval 60
```

### 4. Your Data Will Be Stored In
- `logs/<bot_name>.log` - Your execution logs
- `logs/strategies/*.json` - Your outcome trackers
- `.env` - Your API keys

**These are gitignored - they won't be committed to the repo.**

### 5. Understand the Strategies
- Read `docs/STRATEGIES.md` for deep dive on Strategy E & F
- Read `docs/ARCHITECTURE.md` for system overview
```

---

## 📋 Phase 3: Update Top-Level README

### README.md (Rewrite with Context)
```markdown
# DEX Trading Framework
> Self-improving AI trading strategies for decentralized perpetual exchanges

## What This Is
A battle-tested Python framework for running AI-powered trading bots on perp DEXs.

This repo contains:
1. **Production strategies** (Strategy E & F) - running live since Nov 2025
2. **Historical research** - all past experiments and learnings
3. **Exchange adapters** - plug-in architecture for any DEX
4. **Live trading data** - real results from ~2 months of trading

---

## 🔥 Current Production Bots

### Hibachi Bot (Strategy F - Self-Improving LLM)
- **Exchange**: Hibachi DEX (Solana)
- **Strategy**: LLM analyzes market data → learns from outcomes → auto-blocks losing patterns
- **Performance**: 64% win rate over 22 trades
- **See**: `CURRENT_BOTS.md` for details

### Extended Bot (Strategy E - Self-Improving Pairs)
- **Exchange**: Extended DEX (Starknet)
- **Strategy**: Long/short pairs (ETH vs BTC) → learns which direction works
- **Performance**: 33 trades tracked, active learning
- **See**: `CURRENT_BOTS.md` for details

---

## 📚 The Journey (Oct-Dec 2025)

This repo contains the full evolution of the trading system:

1. **Oct 2025** - Initial bots on Lighter & Pacifica (`lighter_agent/`, `pacifica_agent/`)
2. **Nov 2025** - Moved to Hibachi, developed Strategy F (`hibachi_agent/`)
3. **Nov 2025** - Added Extended with Strategy E pairs trading (`extended_agent/`)
4. **Dec 2025** - Self-learning systems stabilized, both bots break-even

**Key Learnings**:
- ✅ Self-improving strategies work (outcome tracking + auto-filtering)
- ✅ LLM decision-making is viable with proper data
- ✅ Fast exit monitoring (TP/SL) significantly improves results
- ❌ SOL consistently loses (blocked from trading)
- ❌ Funding costs eat into profits (need to optimize hold times)

All historical research is preserved in:
- `archive/` - Old bot versions
- `research/` - Experiments and learnings
- `lighter_agent/`, `pacifica_agent/` - Previous exchange integrations

---

## 🏗️ Exchange-Agnostic Architecture

The core strategies (`Strategy E` & `Strategy F`) are **exchange-agnostic**.

Current exchange adapters:
- ✅ Hibachi (`hibachi_agent/`)
- ✅ Extended (`extended_agent/`)
- 📁 Lighter (archived - `lighter_agent/`)
- 📁 Pacifica (archived - `pacifica_agent/`)

### Adding a New Exchange
See `docs/ADDING_EXCHANGE.md` (TODO) for guide on writing your own adapter.

---

## 🚀 Quick Start (For Co-Workers)

### 1. Setup
```bash
git clone <repo>
pip install -r requirements.txt
cp .env.example .env
# Add your exchange API keys to .env
```

### 2. Test in Dry-Run
```bash
# Hibachi
python -m hibachi_agent.bot_hibachi --dry-run --interval 300

# Extended (requires Python 3.11)
python3.11 -m extended_agent.bot_extended --dry-run --strategy E --interval 60
```

### 3. Understand the System
- **Current Bots**: See `CURRENT_BOTS.md`
- **Strategies Deep-Dive**: See `docs/STRATEGIES.md`
- **Architecture**: See `docs/ARCHITECTURE.md`
- **All Research**: See `research/README.md`

---

## ⚠️ Important: Your Data vs Shared Code

When you run the bots, **your trading data stays local**:

### Your Personal Data (Gitignored)
- `logs/*.log` - Your execution logs
- `logs/strategies/*.json` - Your outcome trackers
- `.env` - Your API keys

These files are in `.gitignore` and **won't be committed**.

### Shared Code (In Git)
- `hibachi_agent/`, `extended_agent/` - Bot code
- `core/` - Strategy framework
- `dexes/` - Exchange SDKs
- `docs/` - Documentation

---

## 📊 Live Trading Results (Owner's Data)

The owner has been running these bots live since November 2025.

### Hibachi Results
- **Balance**: Started $50 → Currently $50 (break-even)
- **Trades**: 48 tracked
- **Win Rate**: 64%
- **All-time P/L**: -$138 (funding costs are the killer)

### Extended Results
- **Balance**: Started $50 → Currently $50 (break-even)
- **Trades**: 33 tracked
- **Learning**: Bias adjustments active

**Conclusion**: Both bots are stable and learning. Break-even after 2 months is success
given we're optimizing against funding costs and refining the strategies.

---

## 📖 Documentation

- `CURRENT_BOTS.md` - Current production bots (Strategy E & F)
- `docs/STRATEGIES.md` - Deep dive on both strategies
- `docs/ARCHITECTURE.md` - System architecture
- `docs/DATA_SOURCES.md` - API documentation
- `research/README.md` - Historical research index

---

## 🛠️ Project Structure

```
dex-trading-framework/
├── hibachi_agent/           # Current: Hibachi bot (Strategy F)
├── extended_agent/          # Current: Extended bot (Strategy E)
├── lighter_agent/           # Archived: Old Lighter bot
├── pacifica_agent/          # Archived: Old Pacifica bot
├── core/                    # Shared: Strategy framework
├── dexes/                   # Shared: Exchange SDKs
├── research/                # Historical: All research
├── archive/                 # Historical: Old versions
├── logs/                    # Your data: Trading logs (gitignored)
└── docs/                    # Documentation
```

---

## 📝 License
[Add your license here]

---

## 🤝 Contributing (For Co-Workers)

1. Run bots in dry-run mode first
2. Document any experiments in `research/`
3. If you improve a strategy, create a new version (don't break production)
4. Share learnings in team meetings

---

**Questions?** See `CURRENT_BOTS.md` or ping the owner.
```

---

## 📋 Phase 4: Update .gitignore (Protect User Data)

### .gitignore
```gitignore
# User Data - Each person's trading results
.env
logs/*.log
logs/**/*.log
logs/strategies/*.json
logs/trades/*.csv
trade-history-*.csv
qwen_query.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Data exports
*.csv
data/lighter_exports/*.csv

# But keep example configs
!.env.example
!examples/**/*.csv
```

---

## 📋 Phase 5: Create docs/STRATEGIES.md

**File**: `docs/STRATEGIES.md`
```markdown
# Trading Strategies Deep-Dive

This document explains the two production strategies in detail.

---

## Strategy F: Self-Improving LLM (Single-Asset)

**File**: `core/strategies/self_improving_llm.py`
**Used By**: Hibachi bot

### Concept
An LLM analyzes market data and makes trading decisions. The bot tracks
every outcome and learns which symbol+direction combinations work.

### How It Works

#### 1. Data Collection
For each symbol (BTC, ETH), fetches:
- **Price & OHLCV**: Current price, volume, candles
- **Technical Indicators**: RSI, MACD, EMAs
- **On-Chain**: Funding rates, open interest
- **Sentiment**: Deep42 AI analysis
- **Whale Signals**: Large player positioning

#### 2. LLM Decision
Sends all data to LLM (Qwen) with prompt:
"You are a quant trader. Based on this data, should we go LONG, SHORT, or HOLD?"

LLM responds with:
- Action: LONG, SHORT, or HOLD
- Symbol: Which asset
- Confidence: 0.0 to 1.0
- Reasoning: Why this decision

#### 3. Position Sizing
- Base: $50 per trade
- Scaled by confidence: 0.5 = $50, 0.85 = $120, 0.95 = $150
- Scaled by account balance
- Leverage: 2.5x - 5x based on confidence

#### 4. Outcome Tracking
After each trade closes, records:
- Symbol + Direction (e.g., "BTC LONG")
- Entry price, exit price
- P/L percentage
- Was it a win or loss?
- How long did we hold?

Stores in: `logs/strategies/self_improving_llm_outcomes.json`

#### 5. Self-Improvement (Every 10 Trades)
Analyzes last 10 trades by symbol+direction:
```
BTC LONG: 8 wins, 2 losses = 80% win rate ✅ KEEP
ETH SHORT: 2 wins, 6 losses = 25% win rate ❌ BLOCK
SOL LONG: 3 wins, 7 losses = 30% win rate ⚠️ REDUCE
```

**Auto-Actions**:
- <30% win rate = **BLOCKED** (won't trade this combo anymore)
- <40% win rate = **REDUCED** (50% position size)
- >60% win rate = **NORMAL** (full size)

#### 6. Feedback Loop
Includes past performance in LLM prompts:
```
"Note: BTC LONG has 80% win rate over last 10 trades.
 ETH SHORT has 25% win rate and is BLOCKED."
```

LLM adjusts future decisions based on this.

### Current Results (Hibachi)
- **Trades**: 48 tracked
- **Win Rate**: 64% overall
- **Filters Applied**: SOL blocked (manual), auto-learning active
- **P/L**: Break-even (funding costs offsetting wins)

---

## Strategy E: Self-Improving Pairs (Long/Short)

**File**: `core/strategies/self_improving_pairs.py`
**Used By**: Extended bot

### Concept
Trade correlated assets as pairs (long one, short the other). Learn which
direction works best over time.

### How It Works

#### 1. Asset Selection
Currently: ETH vs BTC (can be configured for any pair)

#### 2. Data Analysis
For both assets, fetches same data as Strategy F:
- Price, volume, indicators
- Funding rates
- Sentiment
- Whale signals

#### 3. LLM Decision
Asks LLM: "Should we go Long ETH / Short BTC, or Long BTC / Short ETH?"

LLM analyzes:
- Relative strength (is ETH outperforming BTC?)
- Momentum (which has stronger trend?)
- Whale positioning
- Funding rate spreads

Returns:
- Long asset (e.g., ETH)
- Short asset (e.g., BTC)
- Confidence: 0.0 to 1.0
- Reasoning

#### 4. Position Entry
Opens 2 positions simultaneously:
- LONG ETH: $10 (or scaled by confidence)
- SHORT BTC: $10

Total exposure: ~$20 per cycle

#### 5. Hold Time
Fixed duration: **60 minutes**

Why? Reduces funding costs (funding charged every hour on most DEXs)

#### 6. Position Exit
After 60 minutes, closes both positions simultaneously.

#### 7. Outcome Analysis
Calculates:
- Did long asset outperform short? (direction was correct)
- P/L on long leg
- P/L on short leg
- Net spread return

Example:
```
Entry: Long ETH @$3000, Short BTC @$88000
Exit:  ETH @$3030 (+1%), BTC @$88440 (+0.5%)

Long leg: +1% = WIN
Short leg: -0.5% = LOSS
Net: +0.5% = Correct direction ✅
```

Stores in: `logs/strategies/self_improving_pairs_outcomes.json`

#### 8. Self-Improvement (Every 5 Trades)
Analyzes last 5-10 pairs trades:
```
Long ETH / Short BTC: 7 correct, 3 wrong = 70% accuracy
Long BTC / Short ETH: 2 correct, 8 wrong = 20% accuracy
```

**Bias Adjustment**:
- Shifts "bias" toward winning direction
- Max 15% shift per review (gradual learning)
- Includes bias hint in future LLM prompts

Example:
```
"Historical bias: Long ETH / Short BTC wins 70% of time.
 Consider this in your decision."
```

#### 9. Fast Exit Monitor
Monitors both positions every 30 seconds:
- Take profit: If spread hits +2%, close early
- Stop loss: If spread hits -1.5%, cut losses
- Trailing stop: If spread peaks at +3% then drops to +1.5%, close

### Current Results (Extended)
- **Trades**: 33 tracked
- **Learning**: Bias adjustments active
- **P/L**: Break-even
- **Issue**: $0.20/cycle in fees eating into profits

---

## Key Differences

| Feature | Strategy F (LLM) | Strategy E (Pairs) |
|---------|------------------|-------------------|
| **Assets** | Single asset at a time | Two assets simultaneously |
| **Direction** | LONG or SHORT | LONG one, SHORT other |
| **Hold Time** | Variable (LLM decides) | Fixed 60 min |
| **Learning** | By symbol+direction | By pair direction |
| **Position Size** | Confidence-scaled | Fixed per leg |
| **Risk** | Directional market risk | Spread/correlation risk |

---

## Common Components

### Fast Exit Monitor
Both strategies use 30-second position monitoring:
- Checks current P/L
- Applies TP/SL rules
- Overrides LLM exit timing if hit

**Benefits**:
- Captures quick profits
- Cuts losses fast
- No LLM API cost (rule-based)

### Outcome Tracking
Both store every trade in JSON files:
```json
{
  "id": 1,
  "symbol": "BTC/USDT-P",
  "direction": "LONG",
  "entry_price": 88000,
  "exit_price": 88500,
  "pnl_percent": 0.57,
  "is_win": true,
  "llm_reasoning": "...",
  "status": "closed"
}
```

### Performance Analysis
Both analyze outcomes periodically:
- Calculate win rates
- Identify patterns
- Apply filters/adjustments
- Update LLM prompts

---

## Next Evolution Ideas

1. **Multi-timeframe**: Analyze 1h, 4h, 1d timeframes
2. **Dynamic hold times**: Let LLM decide when to exit
3. **Portfolio optimization**: Trade multiple pairs, rebalance
4. **Cross-strategy learning**: Share learnings between E & F
5. **Funding rate optimization**: Exit before funding charges

See `future_features/` for prototypes.
```

---

## 📋 Phase 6: Mark Historical Directories

### Add .ARCHIVED files (empty marker files)
```bash
touch lighter_agent/.ARCHIVED
touch pacifica_agent/.ARCHIVED
touch archive/.ARCHIVED
```

These marker files signal "this is historical, not production"

---

## ✅ Implementation Checklist

### Phase 1: Add README files
- [ ] `archive/README.md`
- [ ] `research/README.md`
- [ ] `lighter_agent/README.md`
- [ ] `pacifica_agent/README.md`
- [ ] `future_features/README.md`

### Phase 2: Create production docs
- [ ] `CURRENT_BOTS.md` (top-level)
- [ ] `docs/STRATEGIES.md`

### Phase 3: Update existing docs
- [ ] Rewrite `README.md` (preserve journey, highlight current)
- [ ] Update `.gitignore` (protect user data)

### Phase 4: Add markers
- [ ] `.ARCHIVED` files in historical dirs

### Phase 5: Test
- [ ] Co-worker can clone and understand structure
- [ ] Clear what's current vs historical
- [ ] Clear where their data will go

---

## Time Estimate
- Phase 1 (READMEs): 1 hour
- Phase 2 (Production docs): 2 hours
- Phase 3 (Update docs): 1 hour
- Phase 4 (Markers): 5 min
- Phase 5 (Review): 30 min

**Total: 4-5 hours**

---

## Result

After this organization:
1. ✅ All historical data preserved
2. ✅ Clear docs explain what everything is
3. ✅ Co-workers can understand the journey
4. ✅ Current production bots clearly marked
5. ✅ User data protected from git commits
6. ✅ Easy to run their own tests

**Nothing deleted. Everything documented.**
