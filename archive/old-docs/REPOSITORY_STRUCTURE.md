# Repository Structure & Complete Inventory

**Last Updated**: November 24, 2025
**Purpose**: Complete map of repository organization and file inventory

---

## Quick Navigation

```
pacifica-trading-bot/
├── 📄 Core Documentation (Root)
│   ├── README.md              # Project overview
│   ├── CLAUDE.md              # Development guide
│   └── REPOSITORY_STRUCTURE.md # ⭐ This file
│
├── 🤖 ACTIVE BOT
│   └── lighter_agent/         # ✅ Lighter Trading Bot (LIVE)
│
├── 🧠 SHARED MODULES
│   ├── llm_agent/             # LLM decision engine & indicators
│   ├── dexes/                 # DEX SDKs
│   └── utils/                 # Shared utilities
│
├── 🔮 FUTURE
│   ├── future_features/       # Planned features research
│   ├── pacifica_agent/        # Future Pacifica bot (paused)
│   └── llm_agent/             # Legacy LLM bot (paused)
│
├── 📚 DOCUMENTATION
│   ├── docs/                  # Project documentation
│   └── research/              # Organized research notes
│
├── 🛠️ INFRASTRUCTURE
│   ├── config.py              # Global config
│   ├── trade_tracker.py       # Trade tracking
│   ├── scripts/               # Utility scripts
│   ├── logs/                  # Bot logs (gitignored)
│   └── data/                  # Data exports
│
└── 🗄️ ARCHIVE
    └── archive/               # Historical code
```

---

## Root Directory Files

### Core Documentation
| File | Purpose | Status |
|------|---------|--------|
| `README.md` | Project overview and quickstart | ✅ Active |
| `CLAUDE.md` | Development guide for AI assistants | ✅ Active |
| `REPOSITORY_STRUCTURE.md` | This file - complete repo map | ✅ Active |

### Configuration
| File | Purpose | Status |
|------|---------|--------|
| `config.py` | Global trading configuration | ✅ Active |
| `trade_tracker.py` | Trade tracking (used by bots) | ✅ Active |
| `requirements.txt` | Python dependencies | ✅ Active |
| `.env` | API keys (gitignored) | ✅ Active |
| `.env.example` | API key template | ✅ Active |
| `.gitignore` | Git ignore patterns | ✅ Active |
| `.mcp.json` | MCP server configuration | ✅ Active |

---

## Active Bot: Lighter Agent

**Directory**: `lighter_agent/`
**Status**: ✅ **LIVE IN PRODUCTION**
**Last Updated**: November 19, 2025

### Structure
```
lighter_agent/
├── bot_lighter.py              # ⭐ Main entry point
├── data/
│   ├── __init__.py
│   ├── market_data_aggregator.py  # Fetch market data from Lighter
│   └── deep42_client.py        # Deep42 macro sentiment (optional)
└── execution/
    ├── __init__.py
    ├── trade_executor.py       # Execute trades on Lighter
    └── hard_exit_rules.py      # Force exit rules (profit/stop targets)
```

### Dependencies
- **Imports from**: `llm_agent/llm/` (LLM decision engine)
- **Imports from**: `llm_agent/data/` (Indicators, OI, funding)
- **Uses**: `dexes/lighter/lighter_sdk.py` (Lighter SDK)
- **Uses**: `trade_tracker.py` (Track trades)

### Key Features
- 101+ markets dynamically loaded from Lighter API
- Zero trading fees
- AI-driven decisions with comprehensive market data
- Deep42 macro context (optional)
- Strategy switching system (logged to `logs/strategy_switches.log`)
- Hard exit rules (profit targets, stop losses)

---

## Shared Modules

### LLM Agent (`llm_agent/`)

**Status**: ✅ **SHARED BY ALL BOTS**
**Purpose**: LLM decision engine and market data processing

#### Structure
```
llm_agent/
├── llm/                        # LLM Decision Engine
│   ├── __init__.py
│   ├── model_client.py         # DeepSeek Chat API client
│   ├── prompt_formatter.py     # Format prompts for LLM
│   ├── response_parser.py      # Parse LLM decisions
│   └── trading_agent.py        # Main LLM agent
│
├── data/                       # Market Data Processing
│   ├── __init__.py
│   ├── indicator_calculator.py # RSI, MACD, EMA calculations
│   ├── oi_fetcher.py          # Open Interest from Cambrian
│   ├── funding_fetcher.py     # Funding rates from Cambrian
│   └── deep42_client.py       # Deep42 macro sentiment
│
├── prompts_archive/            # Historical prompts
│   ├── v4_momentum_strategy.txt
│   └── v5_swing_strategy_pacifica.txt
│
└── config_prompts.py          # Prompt configurations
```

#### Dependencies
- **Used by**: `lighter_agent/`, `pacifica_agent/`, `llm_agent/` (legacy)
- **Requires**: DeepSeek API key, Cambrian API key
- **Provides**: AI decision-making, market indicators, macro context

---

### DEX SDKs (`dexes/`)

**Status**: ✅ **ACTIVE**
**Purpose**: Wrapper SDKs for decentralized exchanges

#### Structure
```
dexes/
├── lighter/
│   ├── __init__.py
│   └── lighter_sdk.py          # Lighter DEX SDK wrapper
│
├── pacifica/
│   ├── __init__.py
│   ├── pacifica_sdk.py         # Pacifica DEX SDK wrapper
│   └── adapter.py              # Pacifica API adapter
│
└── hibachi/                    # ✅ NEW: November 24, 2025
    ├── __init__.py
    └── hibachi_sdk.py          # Hibachi DEX SDK wrapper
```

#### Lighter SDK
- **File**: `dexes/lighter/lighter_sdk.py`
- **Features**: Get balances, positions, market data, create orders
- **Account**: Index 341823, API Key Index 2
- **Markets**: 101+ perpetual pairs

#### Pacifica SDK
- **File**: `dexes/pacifica/pacifica_sdk.py`
- **Features**: Get balances, positions, create orders
- **Account**: `YOUR_ACCOUNT_PUBKEY`
- **Status**: Working but bot is paused

#### Hibachi SDK ⭐ NEW
- **File**: `dexes/hibachi/hibachi_sdk.py`
- **Features**: Get balances, positions, market data, create orders, HMAC authentication
- **Account**: ID 22919, Balance $58.08 USDT
- **Markets**: 15 perpetual pairs (BTC, ETH, SOL, SUI, XRP, etc.)
- **Status**: ✅ **COMPLETE - Ready for bot integration**
- **Docs**: `research/hibachi/API_REFERENCE.md`

---

### Utilities (`utils/`)

**Status**: ✅ **ACTIVE**

#### Files
```
utils/
├── __init__.py
└── shared_rate_limiter.py      # Shared rate limiter for APIs
```

---

## Future Features

### Directory: `future_features/`

**Status**: 🔮 **RESEARCH COMPLETE, AWAITING IMPLEMENTATION**

#### Structure
```
future_features/
├── README.md                   # Future features overview
└── cross_dex_arbitrage.md      # Cross-DEX spread arbitrage research
```

#### Cross-DEX Spread Arbitrage
- **Research Status**: Complete
- **Priority**: Medium
- **Requirements**: Paradex or Extended account setup
- **Description**: Monitor spreads between Lighter, Extended, Paradex
- **Strategy**: Delta-neutral arbitrage (long cheap, short expensive)

---

## Paused/Legacy Bots

### Pacifica Agent (`pacifica_agent/`)

**Status**: 🔮 **PAUSED - FUTURE PHASE 2**

#### Structure
```
pacifica_agent/
├── bot_pacifica.py             # Pacifica bot (paused)
├── data/
│   ├── market_data_aggregator.py
│   └── deep42_client.py
└── execution/
    └── trade_executor.py
```

- **Why Paused**: Focusing on Lighter bot first
- **Future Plan**: Apply Lighter improvements to Pacifica
- **Status**: Working but not running

### Legacy LLM Agent (`llm_agent/`)

**Note**: `llm_agent/` directory contains BOTH shared modules (llm/, data/) AND legacy bot code

#### Legacy Bot Files (Not Used)
```
llm_agent/
├── bot_llm.py                  # 🗄️ Legacy unified bot (unused)
└── execution/                  # 🗄️ Legacy execution (unused)
    ├── __init__.py
    └── trade_executor.py
```

These files exist but are NOT used. Each bot (lighter_agent, pacifica_agent) has its own execution layer.

---

## Documentation

### Docs Directory (`docs/`)

**Status**: ✅ **ACTIVE**

#### Structure
```
docs/
├── AGENTS.md                   # Bot agent documentation
├── ARCHITECTURE.md             # System architecture
├── USER_REFERENCE.md           # Quick command reference
├── PROGRESS.md                 # Project progress log
├── TODO.md                     # Todo list
├── DEPLOYMENT_COMPLETE.md      # Deployment notes
├── DATA_SOURCES_SUMMARY.md     # API data sources
├── STRATEGY_MANAGEMENT.md      # Strategy switching system
└── composer_agent/             # Composer agent docs
    └── COMPOSER_DASHBOARD.md
```

---

### Research Directory (`research/`)

**Status**: ✅ **ORGANIZED**
**Last Cleanup**: November 24, 2025

#### Structure
```
research/
├── README.md                   # Research directory guide
│
├── Active Research (By Topic)
│   ├── agent-lightning/        # Agent Lightning framework
│   ├── cambrian/               # Cambrian API integration
│   ├── deep42/                 # Deep42 macro sentiment
│   ├── deepseek/               # DeepSeek LLM API
│   ├── funding-rates/          # Funding rate analysis
│   ├── hibachi/                # ⭐ NEW: Hibachi DEX integration
│   │   ├── API_REFERENCE.md
│   │   └── INTEGRATION_COMPLETE.md
│   ├── lighter/                # Lighter DEX research
│   ├── moon-dev/               # Moon Dev RBI agent
│   ├── pacifica/               # Pacifica DEX research
│   ├── scripts/                # Research scripts
│   ├── sentient-example-questions/ # Sentient AI examples
│   └── strategies/             # Strategy research
│
└── Completed/Historical Research
    ├── Nov2024-lighter-research/   # Nov 2024 Lighter integration
    ├── Nov2024-v2-research/        # Nov 2024 V2 bot research
    ├── implementation/             # Implementation docs
    ├── archived/                   # Archived research
    └── misc/                       # Miscellaneous research
```

---

## Infrastructure

### Logs Directory (`logs/`)

**Status**: ✅ **ACTIVE** (gitignored)

#### Key Log Files
```
logs/
├── lighter_bot.log             # ⭐ Current Lighter bot log
├── strategy_switches.log       # Strategy change history
├── trades/                     # Trade history by strategy
│   ├── lighter_current.json    # Current trades
│   └── archive/                # Archived trades by strategy
└── (many historical log files)
```

**Note**: Log files are gitignored and not committed

---

### Data Directory (`data/`)

**Status**: ✅ **ACTIVE**

#### Structure
```
data/
└── lighter_exports/            # Lighter trade exports (CSV)
```

---

### Scripts Directory (`scripts/`)

**Status**: ✅ **ACTIVE**
**Purpose**: Testing, debugging, and utility scripts

#### Structure
```
scripts/
├── general/                    # General utilities
│   ├── clean_tracker.py
│   └── switch_strategy.py
├── lighter/                    # Lighter-specific scripts
├── pacifica/                   # Pacifica-specific scripts
├── hibachi/                    # ⭐ NEW: Hibachi-specific scripts
├── rbi_agent/                  # RBI agent scripts
│   ├── fix_and_run_backtest.py
│   └── show_all_returns.py
├── research/                   # Research scripts
└── test_hibachi_markets.py     # ⭐ NEW: Hibachi SDK test script
```

---

### Configuration Directory (`config/`)

**Status**: ✅ **ACTIVE**

#### Structure
```
config/
└── (configuration files)
```

---

## Archive

### Archive Directory (`archive/`)

**Status**: 🗄️ **HISTORICAL REFERENCE ONLY**

#### Structure
```
archive/
├── 2025-10-30/                 # Oct 30 old bot code
├── 2025-11-03-cleanup/         # Nov 3 cleanup
├── 2025-11-03-docs/            # Nov 3 old docs
├── 2025-11-05-cleanup/         # Nov 5 cleanup
├── 2025-11-07-old-pacifica-framework/  # Old Pacifica framework
├── 2025-11-07-v2-deployment-docs/      # Old deployment docs
├── old_bots/                   # Old bot executables
└── old_strategies/             # Old strategy implementations
```

**⚠️ IMPORTANT**: Do NOT use any code from archive/. All old bots have been replaced.

---

## External Dependencies

### Moon Dev Reference (`moon-dev-reference/`)

**Status**: 📚 **REFERENCE**
**Purpose**: Moon Dev framework reference (git submodule)

#### Structure
```
moon-dev-reference/
├── docs/                       # Moon Dev documentation
├── src/                        # Moon Dev source code
└── moon-dev-reference/         # Submodule files
```

**Note**: This is a git submodule, not actively used in production

---

## Hidden Directories

### Task Master (`.taskmaster/`)

**Status**: ✅ **ACTIVE** (if using Task Master)

```
.taskmaster/
├── tasks/                      # Task files
│   └── tasks.json
├── docs/                       # Task Master docs
├── reports/                    # Analysis reports
├── config.json                 # Task Master config
└── CLAUDE.md                   # Task Master integration guide
```

### Claude (`.claude/`)

**Status**: ✅ **ACTIVE** (if configured)

```
.claude/
├── settings.json               # Claude Code settings
└── commands/                   # Custom slash commands
```

---

## File Statistics

### Root Level
- **Total markdown files**: 3 (README, CLAUDE, REPOSITORY_STRUCTURE)
- **Total Python files**: 2 (config.py, trade_tracker.py)
- **Total config files**: 5 (.env, .env.example, .gitignore, .mcp.json, requirements.txt)

### Active Bot (lighter_agent/)
- **Total Python files**: 6
- **Lines of code**: ~1500

### Shared Modules (llm_agent/)
- **Total Python files**: 10+
- **Lines of code**: ~3000

### Research Directory
- **Total subdirectories**: 21
- **Total markdown files**: 50+

---

## Development Workflow

### Adding New Features
1. Research in `research/[topic]/`
2. If future feature → document in `future_features/`
3. Implement in `lighter_agent/` or `pacifica_agent/`
4. Test with scripts in `scripts/`
5. Deploy and log to `logs/`
6. Update this file (REPOSITORY_STRUCTURE.md)

### Deprecating Code
1. Move to `archive/[YYYY-MM-DD]/`
2. Add comment in replacement referencing archive
3. Update this file
4. Update CLAUDE.md if needed

### Research Workflow
1. Create topic folder in `research/[topic]/`
2. Document findings in markdown
3. When complete, move to `research/archived/` or `research/Nov2024-*/`
4. Update `research/README.md`

---

## Key Principles

1. **Single Active Bot**: Only `lighter_agent/` runs in production
2. **Shared Modules**: `llm_agent/llm/` and `llm_agent/data/` are shared
3. **Clean Root**: Only 3 markdown files in root (README, CLAUDE, REPOSITORY_STRUCTURE)
4. **Organized Research**: Topic-based folders, completed research timestamped
5. **Everything Tracked**: This file tracks ALL directories and files
6. **Archive Don't Delete**: Move old code to archive/ with timestamp

---

## Future Plans

### Short Term (Next Week)
- Continue optimizing Lighter bot strategies
- Monitor for new profitable patterns
- Document strategy performance
- **NEW**: Build Hibachi bot agent (SDK ready, $58.08 funded)

### Medium Term (Next Month)
- Deploy Hibachi bot (15 markets, 0.045% taker fee)
- Consider cross-DEX spread arbitrage (if profitable)
- Evaluate Extended or Paradex integration

### Long Term (Phase 2)
- Apply Lighter improvements to Pacifica bot
- Multi-exchange orchestration (Lighter + Hibachi + Pacifica)
- Dual/triple airdrop farming potential

---

**Last Updated**: November 24, 2025
**Maintained By**: AI Agent (Claude Code)
**Update Frequency**: After major changes or reorganization
