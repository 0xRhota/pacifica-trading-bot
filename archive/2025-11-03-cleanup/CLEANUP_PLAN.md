# Repository Cleanup Plan

**Date**: 2025-11-03  
**Status**: 📋 PLANNING (NOT YET EXECUTED)  
**Purpose**: Organize repo for three distinct systems, remove test scripts, archive valuable old code

---

## 🎯 Three Core Systems

### 1. **Pacifica Trading Bot** (LLM-Based)
- **Location**: `llm_agent/`
- **Entry Point**: `llm_agent/bot_llm.py`
- **Status**: ✅ LIVE (running)
- **Purpose**: LLM-driven trading on Pacifica DEX
- **Key Files**:
  - `llm_agent/bot_llm.py` - Main bot orchestrator
  - `llm_agent/llm/trading_agent.py` - LLM decision engine
  - `llm_agent/execution/trade_executor.py` - Trade execution
  - `llm_agent/data/aggregator.py` - Data pipeline
  - `llm_agent/llm/prompt_formatter.py` - Prompt system
- **Logs**: `logs/llm_bot.log`
- **Config**: Uses `.env` (PACIFICA_PRIVATE_KEY, etc.)

### 2. **Lighter Trading Bot** (Sister Bot - TO BE IMPLEMENTED)
- **Location**: `lighter_agent/` (TO BE CREATED)
- **Entry Point**: `lighter_agent/bot_lighter.py` (TO BE CREATED)
- **Status**: 🚧 PLANNED (similar structure to Pacifica bot)
- **Purpose**: LLM-driven trading on Lighter DEX
- **Requirements**:
  - Similar structure to Pacifica bot
  - Separate logging (`logs/lighter_bot.log`)
  - Ability to change strategies
  - Uses Lighter SDK (`dexes/lighter/lighter_sdk.py`)
- **Config**: Uses `.env` (LIGHTER_API_KEY_PRIVATE, LIGHTER_ACCOUNT_INDEX=341823, etc.)

### 3. **Backtesting Bot** (RBI Agent)
- **Location**: `rbi_agent/`
- **Entry Point**: `rbi_agent/run_moon_dev_rbi.py`
- **Status**: ✅ ACTIVE (running)
- **Purpose**: Automated strategy discovery and backtesting
- **Key Files**:
  - `rbi_agent/run_moon_dev_rbi.py` - Main runner
  - `rbi_agent/cambrian_csv_adapter.py` - Data adapter
  - `moon-dev-reference/src/agents/rbi_agent_pp_multi.py` - Moon Dev's RBI agent
- **Logs**: `logs/moon_dev_rbi.log`
- **Data**: Uses Cambrian API for historical OHLCV

---

## 🗑️ Files to DELETE (Test Scripts - No Longer Needed)

### Lighter Setup/Test Scripts (All in `scripts/lighter/`)
**Reason**: Connection is now working, account_index found (341823), these are one-time setup scripts

**DELETE**:
- ❌ `scripts/lighter/diagnose_lighter_setup.py`
- ❌ `scripts/lighter/discover_lighter_config.py`
- ❌ `scripts/lighter/find_account_index.py` (replaced by API call)
- ❌ `scripts/lighter/find_account_via_api.py` (one-time use)
- ❌ `scripts/lighter/find_account_with_key_validation.py` (one-time use)
- ❌ `scripts/lighter/find_correct_account.py` (one-time use)
- ❌ `scripts/lighter/find_lighter_api_key.py` (one-time use)
- ❌ `scripts/lighter/get_actual_account_index.py` (one-time use)
- ❌ `scripts/lighter/test_connection_simple.py` (one-time use)
- ❌ `scripts/lighter/test_lighter_connection_detailed.py` (one-time use)
- ❌ `scripts/lighter/test_lighter_connection.py` (one-time use)
- ❌ `scripts/lighter/test_with_account_2.py` (one-time use)
- ❌ `scripts/lighter/test_order_minimal.py` (one-time test)
- ❌ `scripts/lighter/test_trade.py` (one-time test)
- ❌ `scripts/lighter/test_lighter_order.py` (one-time test)
- ❌ `scripts/lighter/test_open_position.py` (one-time test)
- ❌ `scripts/lighter/register_lighter_api_key.py` (already registered)
- ❌ `scripts/lighter/setup_lighter_api_key.py` (already set up)
- ❌ `scripts/lighter/explore_lighter_sdk.py` (exploration script)
- ❌ `scripts/lighter/quick_buy.py` (one-time test)
- ❌ `scripts/lighter/buy_sol_manual.py` (manual test)
- ❌ `scripts/lighter/place_sol_order.py` (one-time test)

**KEEP** (Potentially useful for Lighter bot):
- ✅ `scripts/lighter/check_lighter_account.py` - Useful for monitoring
- ✅ `scripts/lighter/check_lighter_account_balance.py` - Useful for monitoring
- ✅ `scripts/lighter/get_markets.py` - Useful for market discovery
- ✅ `scripts/lighter/lighter_bot_simple.py` - Could be reference for Lighter bot

### Other Test Scripts
**DELETE**:
- ❌ `scripts/test_agent_order.py` - Old test script
- ❌ `scripts/test_pacifica_order.py` - Old test script
- ❌ `scripts/research/test_deepseek_api.py` - Test script
- ❌ `scripts/research/test_macro_sources.py` - Test script
- ❌ `scripts/research/test_oi_coverage.py` - Test script

**KEEP**:
- ✅ `scripts/general/clean_tracker.py` - Useful utility
- ✅ `scripts/general/sync_tracker.py` - Useful utility
- ✅ `scripts/rbi_agent/` - Keep all (part of RBI agent system)
- ✅ `scripts/pacifica/` - Keep (if exists, might be useful)

---

## 📦 Files to ARCHIVE (Valuable Old Code)

### Archive to `archive/2025-11-03-cleanup/`

**Archive Old Bot Files** (if not already archived):
- `archive/live_bot.py` - Already in archive ✅
- `archive/live_bot_lighter.py` - Already in archive ✅
- Any other old bot files not yet archived

**Archive Old Strategies** (if not already archived):
- Check `archive/old_strategies/` - Already exists ✅

**Archive Research/Exploration Files**:
- `LIGHTER_RESEARCH_SUMMARY.md` → `archive/2025-11-03-cleanup/`
- `BOT_ANALYSIS_ISSUES.md` → `archive/2025-11-03-cleanup/`
- `WHEN_YOU_RETURN.md` → `archive/2025-11-03-cleanup/` (temporary status file)

**Archive Old Documentation** (consolidate):
- `docs/PROGRESS.md` → Check if duplicate of root `PROGRESS.md`
- Old planning docs that are superseded

---

## 📁 Repository Structure After Cleanup

```
pacifica-trading-bot/
├── 📊 THREE CORE SYSTEMS
│   ├── llm_agent/              # System 1: Pacifica Trading Bot
│   ├── lighter_agent/           # System 2: Lighter Trading Bot (TO BE CREATED)
│   └── rbi_agent/               # System 3: Backtesting Bot
│
├── 📚 Shared Infrastructure
│   ├── dexes/                   # DEX SDKs (Pacifica, Lighter)
│   ├── utils/                   # Shared utilities
│   ├── config.py                # Global config
│   └── trade_tracker.py         # Trade tracking (shared)
│
├── 🛠️ Scripts & Tools
│   ├── scripts/
│   │   ├── general/             # General utilities (clean_tracker, sync_tracker)
│   │   ├── pacifica/            # Pacifica-specific scripts (if any)
│   │   └── rbi_agent/            # RBI agent scripts
│   │   └── lighter/              # Lighter utilities (KEEP: check_account, get_markets)
│   │
├── 📖 Documentation
│   ├── README.md                 # Project overview
│   ├── CLAUDE.md                 # Development guide
│   ├── PROGRESS.md               # Project progress log
│   ├── USER_REFERENCE.md         # Quick command reference
│   ├── AGENTS.md                 # Multi-agent collaboration
│   ├── REPOSITORY_STRUCTURE.md   # File organization index
│   └── docs/                     # Detailed documentation
│
├── 🔬 Research & Archive
│   ├── research/                 # Research findings
│   └── archive/                  # Archived code/docs
│
├── 📦 Dependencies
│   ├── moon-dev-reference/       # Moon Dev RBI agent (git submodule)
│   ├── requirements.txt
│   └── .env.example
│
└── 📝 Logs (gitignored)
    └── logs/
        ├── llm_bot.log           # Pacifica bot logs
        ├── lighter_bot.log       # Lighter bot logs (TO BE CREATED)
        └── moon_dev_rbi.log       # RBI agent logs
```

---

## 📝 Documentation Updates Needed

### 1. Update `README.md`
- Add clear section for "Three Systems"
- Point to each system's entry point
- Add quick start for each system

### 2. Update `REPOSITORY_STRUCTURE.md`
- Mark three systems clearly
- Remove references to deleted test scripts
- Update status indicators

### 3. Update `PROGRESS.md`
- Add entry for cleanup completion
- Document Lighter bot planning

### 4. Create `LIGHTER_BOT_PLAN.md` (NEW)
- Document planned Lighter bot structure
- Reference Pacifica bot as template
- List requirements

### 5. Update `USER_REFERENCE.md`
- Add Lighter bot commands (placeholder)
- Update script references

---

## ✅ Execution Checklist

### Phase 1: Archive Valuable Files
- [ ] Create `archive/2025-11-03-cleanup/`
- [ ] Move `LIGHTER_RESEARCH_SUMMARY.md` → archive
- [ ] Move `BOT_ANALYSIS_ISSUES.md` → archive
- [ ] Move `WHEN_YOU_RETURN.md` → archive
- [ ] Review `archive/` for duplicates

### Phase 2: Delete Test Scripts
- [ ] Delete all Lighter setup/test scripts (19 files)
- [ ] Delete other test scripts (5 files)
- [ ] Verify no critical functionality lost

### Phase 3: Create Lighter Bot Structure
- [ ] Create `lighter_agent/` directory
- [ ] Create `lighter_agent/README.md` (placeholder)
- [ ] Document structure plan

### Phase 4: Update Documentation
- [ ] Update `README.md` with three systems
- [ ] Update `REPOSITORY_STRUCTURE.md`
- [ ] Update `PROGRESS.md`
- [ ] Create `LIGHTER_BOT_PLAN.md`
- [ ] Update `USER_REFERENCE.md`

### Phase 5: Final Verification
- [ ] Verify all three systems are clearly marked
- [ ] Verify test scripts removed
- [ ] Verify archived files in correct location
- [ ] Run `git status` to review changes
- [ ] Commit cleanup changes

---

## 🚨 Important Notes

1. **DO NOT DELETE** until user approves this plan
2. **BACKUP FIRST**: All deletions are reversible via git
3. **VERIFY**: Check each script before deleting to ensure no critical functionality
4. **LIGHTER BOT**: Structure will mirror Pacifica bot, but implementation is separate task
5. **MOON-DEV-REFERENCE**: Keep as git submodule (already handled)

---

## 📊 Summary

**Files to Delete**: ~24 test scripts (mostly Lighter setup scripts)  
**Files to Archive**: ~3 temporary docs  
**New Structure**: Clear separation of 3 systems  
**Documentation**: Updated to reflect new structure  

**Risk Level**: 🟢 LOW (all deletions are test scripts, git history preserved)

---

**Status**: ⏸️ AWAITING USER APPROVAL TO EXECUTE

