# Repository Structure & Documentation Index

**Last Updated**: October 30, 2025
**Purpose**: Complete map of repository organization with status indicators

---

## Status Legend

- ✅ **ACTIVE** - Currently in use, maintained
- 📚 **REFERENCE** - Historical/reference documentation, not actively used
- 🗄️ **ARCHIVED** - Superseded by newer implementations, kept for reference
- 🚧 **WIP** - Work in progress, incomplete
- ⚠️ **OBSOLETE** - No longer relevant, candidate for removal

---

## Root Level Files

### Active Documentation
| File | Status | Purpose | Last Updated |
|------|--------|---------|--------------|
| `README.md` | ✅ ACTIVE | Project overview and quickstart | Oct 2025 |
| `CLAUDE.md` | ✅ ACTIVE | Development guide for Claude Code | Oct 30, 2025 |
| `PROGRESS.md` | ✅ ACTIVE | Project progress log with prompt version history | Oct 31, 2025 |
| `USER_REFERENCE.md` | ✅ ACTIVE | Quick command reference for daily use | Oct 31, 2025 |
| `PROMPT_EXPERIMENTS.md` | ✅ ACTIVE | Guide for prompt experimentation and swapping | Oct 31, 2025 |

### Bot Status & Configuration
| File | Status | Purpose | Last Updated |
|------|--------|---------|--------------|
| `LLM_BOT_STATUS.md` | ✅ ACTIVE | Current LLM bot status and deployment info | Oct 30, 2025 |
| `DYNAMIC_TOKEN_ANALYSIS.md` | ✅ ACTIVE | Token discovery and position re-evaluation docs | Oct 30, 2025 |
| `DEEP42_CUSTOM_QUERIES.md` | ✅ ACTIVE | Deep42 custom macro query implementation | Oct 30, 2025 |
| `DATA_SOURCES_SUMMARY.md` | ✅ ACTIVE | Quick reference for all data sources with attribution | Oct 30, 2025 |

### Historical Planning Documents
| File | Status | Purpose | Notes |
|------|--------|---------|-------|
| `MOON_DEV_RESEARCH.md` | 📚 REFERENCE | Analysis of Moon Dev's trading agent | Completed research, informational |
| `DATA_PIPELINE_IMPLEMENTATION_PLAN.md` | 📚 REFERENCE | Original data pipeline planning | Superseded by actual implementation |
| `RESEARCH_INDEX.md` | 📚 REFERENCE | Index of Moon Dev research | Historical context |

### Security & Audit
| File | Status | Purpose | Last Updated |
|------|--------|---------|--------------|
| `SECURITY_AUDIT_REPORT.md` | ✅ ACTIVE | Security audit findings and fixes | Oct 29, 2025 |

### Configuration Files
| File | Status | Purpose |
|------|--------|---------|
| `.env` | ✅ ACTIVE | Environment variables (gitignored) |
| `.env.example` | ✅ ACTIVE | Template for .env |
| `.env.README` | ✅ ACTIVE | Environment setup guide |
| `.gitignore` | ✅ ACTIVE | Git ignore rules |
| `.mcp.json` | ✅ ACTIVE | MCP server configuration |
| `config.py` | ✅ ACTIVE | Trading configuration (lot sizes, markets, etc.) |
| `requirements.txt` | ✅ ACTIVE | Python dependencies |

---

## `/bots/` - Active Trading Bots

**Status**: 🗄️ ARCHIVED (Legacy bots - replaced by LLM agent)
**Purpose**: Old bot files kept for reference

| File | Status | DEX | Strategy | Notes |
|------|--------|-----|----------|-------|
| `vwap_lighter_bot.py` | 🗄️ ARCHIVED | Lighter | VWAP | Not used - reference only |
| `README.md` | ✅ ACTIVE | - | - | Bot documentation |

**⚠️ IMPORTANT**: All legacy bots have been replaced by the LLM Trading Bot in `/llm_agent/`

---

## `/llm_agent/` - LLM Trading Bot System

**Status**: ✅ ACTIVE - **THIS IS THE ONLY PRODUCTION BOT**
**Purpose**: LLM-powered trading agent (new architecture)
**Running**: PID 83713 | Mode: LIVE | Log: `logs/llm_bot.log`

### Structure
```
llm_agent/
├── bot_llm.py                  # ✅ Main entry point for LLM bot
├── data/
│   ├── macro_context_fetcher.py   # ✅ CoinGecko + macro data
│   ├── market_data_fetcher.py     # ✅ Pacifica market data
│   └── oi_data_fetcher.py         # ✅ Open interest data
├── execution/
│   ├── pacifica_executor.py       # ✅ Trade execution
│   └── position_manager.py        # ✅ Position tracking
├── llm/
│   ├── trading_agent.py            # ✅ Main LLM decision logic
│   ├── prompt_formatter.py         # ✅ Prompt construction (lines 160-191)
│   ├── token_analysis_tool.py      # ✅ Token discovery & Deep42 queries
│   └── deep42_client.py            # ✅ Deep42 API client
└── prompts_archive/               # ✅ NEW: Prompt version archive
    ├── v1_baseline_conservative.txt  # ✅ Original conservative prompt
    ├── v2_aggressive_swing.txt       # ✅ Aggressive swing trading prompt
    └── README.md                     # ✅ Archive documentation
```

**Features**:
- Dynamic token discovery (218 HyperLiquid markets)
- LLM selects 3 tokens to analyze deeply each cycle
- Deep42 sentiment/news/technical analysis
- Position re-evaluation with "close or hold?" guidance
- Custom Deep42 macro queries for time-specific intelligence

**Running Status**: Live bot (PID: 88790), 5-minute cycles

---

## `/strategies/` - Strategy Implementations

**Status**: ✅ ACTIVE
**Purpose**: Trading strategy classes

| File | Status | Type | Notes |
|------|--------|------|-------|
| `base_strategy.py` | ✅ ACTIVE | Abstract base | Strategy interface |
| `vwap_strategy.py` | ✅ ACTIVE | VWAP + OB imbalance | Long/short, active |
| `long_short.py` | 🚧 WIP | Directional | Work in progress |
| `basic_long_only.py` | 🗄️ ARCHIVED | Long-only | Superseded |
| `README.md` | ✅ ACTIVE | - | Strategy docs with performance data |

---

## `/dexes/` - DEX SDK Wrappers

**Status**: ✅ ACTIVE
**Purpose**: Exchange-specific API integrations

### `/dexes/lighter/`
| File | Status | Purpose |
|------|--------|---------|
| `lighter_sdk.py` | ✅ ACTIVE | Lighter DEX SDK wrapper |

**Features**: Market orders, stop-loss, take-profit, account balance, positions

### `/dexes/pacifica/`
| File | Status | Purpose |
|------|--------|---------|
| `pacifica_sdk.py` | ✅ ACTIVE | Pacifica DEX SDK wrapper |

---

## `/scripts/` - Utility Scripts

**Status**: ✅ ACTIVE
**Purpose**: Testing and utility scripts

### Root Scripts
| File | Status | Purpose |
|------|--------|---------|
| `swap_prompt.sh` | ✅ ACTIVE | **NEW**: Swap between prompt versions easily |
| `view_decisions.py` | ✅ ACTIVE | View bot decision summary |
| `view_decision_details.py` | ✅ ACTIVE | View detailed decision breakdown |
| `validate_bot_startup.py` | ✅ ACTIVE | Validate bot started successfully |

### `/scripts/general/`
| File | Status | Purpose |
|------|--------|---------|
| `sync_tracker.py` | ✅ ACTIVE | Sync trade tracker with exchange |
| `place_order_now.py` | ✅ ACTIVE | Manual order placement |

### `/scripts/lighter/`
**Status**: ✅ ACTIVE
**Purpose**: Lighter DEX testing scripts

Files: `check_account.py`, `check_balance.py`, `explore_sdk.py`, `find_account_index.py`, `find_api_key.py`, `get_account_index.py`, `register_api_key.py`, `setup_api_key.py`, `test_connection.py`, `test_order.py`, `test_trade.py`

### `/scripts/pacifica/`
**Status**: (No files yet, would contain Pacifica-specific scripts)

---

## `/research/` - Research & Analysis

**Status**: ✅ ACTIVE
**Purpose**: Strategy research, backtesting, market analysis

### Root Research Files
| File | Status | Topic | Notes |
|------|--------|-------|-------|
| `AGENT_LIGHTNING_RESEARCH.md` | ✅ ACTIVE | Agent Lightning framework | Oct 30, 2025 - Complete analysis |
| `DEEPSEEK_API_TEST.md` | 📚 REFERENCE | DeepSeek API testing | API validation |
| `FUNDING_RATE_IMPLEMENTATION.md` | 📚 REFERENCE | Funding rate implementation | Implementation guide |
| `FUNDING_RATE_QUICK_REFERENCE.md` | 📚 REFERENCE | Funding rate quick ref | API reference |
| `FUNDING_RATE_RESEARCH.md` | 📚 REFERENCE | Funding rate research | Deep dive |
| `FUNDING_RATE_RESEARCH_INDEX.md` | 📚 REFERENCE | Funding rate index | Research index |
| `KNOWLEDGE_GAP_ANALYSIS.md` | 📚 REFERENCE | Knowledge gaps | Assessment |
| `LONG_SHORT_STRATEGY_RESEARCH.md` | 📚 REFERENCE | Long/short strategy | Strategy research |
| `MULTI_DEX_ARCHITECTURE.md` | 📚 REFERENCE | Multi-DEX design | Architecture |
| `PHASE_0_VALIDATION_REPORT.md` | 📚 REFERENCE | Phase 0 validation | Validation report |
| `PRD_FINAL_REVIEW.md` | 📚 REFERENCE | PRD review | Product review |
| `PROFITABLE_STRATEGIES_RESEARCH.md` | 📚 REFERENCE | Profitable strategies | Strategy ideas |
| `VWAP_STRATEGY_IMPLEMENTATION.md` | 📚 REFERENCE | VWAP implementation | Implementation guide |
| `FOLDER_STRUCTURE_PLAN.md` | 📚 REFERENCE | Folder organization | Planning doc |
| `README.md` | ✅ ACTIVE | Research directory guide | - |

### `/research/cambrian/` - Cambrian API Research
**Status**: 📚 REFERENCE
**Files**: `DEEP42_FINDINGS.md`, `DEEP42_PERPDEX_ANALYSIS.md`, `DEEP_RESEARCH_NOTES.md`, `ENDPOINT_TEST_RESULTS.md`, `FINDINGS.md`, `INTEGRATION_PLAN.md`, `README.md`

**Purpose**: Historical Cambrian API research (completed)

### `/research/lighter/` - Lighter DEX Research
**Status**: 📚 REFERENCE
**Files**: `LIGHTER_QUICK_START.md`, `LIGHTER_REQUIREMENTS.md`, `LIGHTER_SETUP_COMPLETE.md`, `LIGHTER_STATUS.md`, `WALLET_SECURITY.md`, `WHEN_YOU_WAKE_UP.md`

**Purpose**: Lighter DEX integration research (completed)

---

## `/docs/` - Core Documentation

**Status**: ✅ ACTIVE
**Purpose**: Project documentation

| File | Status | Purpose | Last Updated |
|------|--------|---------|--------------|
| `DATA_SOURCES.md` | ✅ ACTIVE | Complete API reference (Cambrian, Pacifica, funding rates) | Oct 2025 |
| `LLM_AGENT_STRATEGY_PLAN.md` | 📚 REFERENCE | LLM agent planning | Historical |
| `PROGRESS.md` | 📚 REFERENCE | Progress tracking | Superseded by root PROGRESS.md |
| `SETUP.md` | ✅ ACTIVE | Setup instructions | - |
| `STRATEGY_MANAGEMENT.md` | ✅ ACTIVE | Strategy management guide | - |

---

## `/archive/` - Archived Code

**Status**: 🗄️ ARCHIVED
**Purpose**: Superseded implementations kept for reference

### Root Archive Files
| File | Archived Date | Reason | Can Delete? |
|------|---------------|--------|-------------|
| `live_bot.py` | Oct 2025 | Replaced by live_pacifica.py | No - reference |
| `live_bot_lighter.py` | Oct 2025 | Replaced by vwap_lighter_bot.py | No - reference |
| `DUAL_BOTS_RUNNING.md` | Oct 2025 | Historical status doc | Yes - if desired |
| `LIGHTER_WORKING.md` | Oct 2025 | Historical status doc | Yes - if desired |
| `README.md` | ✅ ACTIVE | Archive documentation | No - explains archive |

### `/archive/2025-10-30/`
| File | Archived Date | Reason | Can Delete? |
|------|---------------|--------|-------------|
| `live_pacifica.py.ARCHIVED` | Oct 30, 2025 | ⚠️ **OBSOLETE** - Replaced by LLM bot | No - reference |

**⚠️ CRITICAL**: `live_pacifica.py` was the old Pacifica bot. It has been fully replaced by the LLM Trading Bot (`llm_agent/bot_llm.py`).

### `/archive/old_bots/`
Archived bot implementations

### `/archive/old_strategies/`
Archived strategy implementations

**⚠️ IMPORTANT**: Do NOT import from or run archived files. They are obsolete. Check git history for context.

---

## `/logs/` - Log Files

**Status**: ✅ ACTIVE
**Purpose**: Bot execution logs

**Structure**:
```
logs/
├── llm_bot.log              # ✅ Current LLM bot log
├── pacifica_live.log        # ✅ Current Pacifica bot log
├── bot_sessions.log         # ✅ Condensed session start/stop log
├── trades/                  # ✅ Trade-specific logs
└── *.log                    # Historical logs
```

**Gitignored**: Yes (*.log)
**Rotation**: Max 7 days or 100MB

---

## `/pacifica/` - Pacifica Module (Subfolder Architecture)

**Status**: 📚 REFERENCE (appears to be duplicate structure)
**Purpose**: Alternative Pacifica module organization

**Note**: This appears to be a duplicate/experimental structure. Primary code is in root-level `/dexes/pacifica/` and `/bots/`. Consider consolidating or archiving.

---

## `/utils/` - Shared Utilities

**Status**: ✅ ACTIVE
**Purpose**: Shared utility functions

| File | Status | Purpose |
|------|--------|---------|
| `vwap.py` | ✅ ACTIVE | Session VWAP calculation |
| `logger.py` | ✅ ACTIVE | Logging configuration |

---

## Root Level Infrastructure Files

| File | Status | Purpose |
|------|--------|---------|
| `config.py` | ✅ ACTIVE | Trading configuration (lot sizes, market IDs) |
| `pacifica_bot.py` | ✅ ACTIVE | PacificaAPI wrapper for market data |
| `risk_manager.py` | ✅ ACTIVE | Position sizing and risk controls |
| `trade_tracker.py` | ✅ ACTIVE | Trade tracking and P&L calculation |
| `monitor.py` | ✅ ACTIVE | Bot monitoring script |
| `setup.py` | ✅ ACTIVE | Package setup |

---

## Hidden/Config Directories

### `/.claude/`
**Status**: ✅ ACTIVE
**Purpose**: Claude Code configuration
**Files**: `settings.json` (tool allowlist, preferences)

### `/.taskmaster/`
**Status**: ✅ ACTIVE
**Purpose**: Task Master AI configuration
**Structure**:
```
.taskmaster/
├── CLAUDE.md              # ✅ Task Master integration guide
├── config.json            # ✅ AI model config
├── tasks/                 # ✅ Task files
├── docs/                  # ✅ PRD documents
├── reports/               # ✅ Analysis reports
└── templates/             # ✅ Templates
```

### `/.git/`
**Status**: ✅ ACTIVE
**Purpose**: Git repository data

---

## Cleanup Recommendations

### Safe to Archive (Move to `/archive/` with timestamp)
1. `DATA_PIPELINE_IMPLEMENTATION_PLAN.md` → Already reference, could archive
2. `RESEARCH_INDEX.md` → Historical, could archive
3. `/pacifica/` subfolder → Appears duplicate, investigate and consolidate or archive

### Safe to Remove (After backup)
1. `live_bot_vwap_lighter.log` (root level) → Empty file, can delete
2. `/archive/DUAL_BOTS_RUNNING.md` → Transient status doc
3. `/archive/LIGHTER_WORKING.md` → Transient status doc

### Keep As-Is
- All `/research/` files (valuable historical context)
- All active bot and strategy files
- All configuration files
- Current documentation

---

## Documentation Navigation Guide

### "I want to..."

**...understand the project**:
- Start: `README.md`
- Then: `CLAUDE.md` (development guide)

**...see what's currently running**:
- `LLM_BOT_STATUS.md` (LLM bot status)
- `logs/bot_sessions.log` (session history)

**...understand the LLM bot**:
- `DYNAMIC_TOKEN_ANALYSIS.md` (token discovery)
- `DEEP42_CUSTOM_QUERIES.md` (macro queries)
- `DATA_SOURCES_SUMMARY.md` (data sources)

**...look up API endpoints**:
- `docs/DATA_SOURCES.md` (complete API reference)
- `DATA_SOURCES_SUMMARY.md` (quick reference)

**...understand strategies**:
- `strategies/README.md` (strategy docs with performance)

**...find research on a topic**:
- `research/AGENT_LIGHTNING_RESEARCH.md` (Agent Lightning)
- `research/cambrian/` (Cambrian API)
- `research/lighter/` (Lighter DEX)

**...see historical decisions**:
- `PROGRESS.md` (high-level progress)
- `MOON_DEV_RESEARCH.md` (Moon Dev analysis)

**...check security**:
- `SECURITY_AUDIT_REPORT.md` (audit findings)

**...set up environment**:
- `.env.README` (environment setup)
- `.env.example` (template)

---

## File Naming Conventions

### Documentation (.md)
- **UPPERCASE.md** (root level) - Major documentation, quick reference
- **lowercase.md** (subdirectories) - Module-specific docs
- **README.md** - Directory guides

### Python (.py)
- **snake_case.py** - All Python files
- **bot_name.py** (bots/) - Bot executables
- **strategy_name.py** (strategies/) - Strategy implementations
- **module_name.py** - Modules and utilities

### Logs (.log)
- **bot_name.log** - Current active logs
- **bot_name_YYYY-MM-DD.log** - Historical logs

---

## Maintenance Guidelines

### When Adding New Files

1. **Documentation**: Place in appropriate directory (`/docs/`, `/research/`)
2. **Bots**: Place in `/bots/` with descriptive name
3. **Strategies**: Place in `/strategies/` with clear name
4. **Scripts**: Place in `/scripts/{dex}/` or `/scripts/general/`
5. **Update this file**: Add entry to relevant section

### When Archiving Files

1. Move to `/archive/` with subdirectory if needed
2. Add timestamp to filename (optional)
3. Update `/archive/README.md` with reason
4. Add reference in this document

### When Deprecating Documentation

1. Change status to 📚 REFERENCE or 🗄️ ARCHIVED
2. Add note explaining superseding document/implementation
3. Keep file (don't delete) for historical context

---

## Quick Status Check

**Active Bots**: 2
- `bots/live_pacifica.py` (running, PID: 55194)
- `llm_agent/bot_llm.py` (running, PID: 88790)

**Active Strategies**: 2
- `strategies/vwap_strategy.py` (VWAP + OB imbalance)
- `strategies/long_short.py` (WIP)

**Active DEXes**: 2
- Pacifica (main)
- Lighter (testing)

**Documentation Status**: Well-organized, needs minor cleanup

**Archived Files**: Properly documented in `/archive/`

**Research Files**: 24 documents (mix of active and reference)

---

**End of Repository Structure Document**
