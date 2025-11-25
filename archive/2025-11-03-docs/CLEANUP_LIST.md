# Repository Cleanup List

## Files to Archive (Move to archive/)

### Experimental Scripts
- `scripts/lighter/` - All test scripts (except useful ones)
- `scripts/research/` - Research experiments
- `scripts/rbi_agent/` - RBI test scripts
- `scripts/general/` - Utility scripts that aren't core

### Confusing/Outdated Docs
- `PROMPT_EXPERIMENTS.md`
- `PROMPT_SYSTEM_STATUS.md`
- `TASK_SWAP_TO_V3.md`
- `STRATEGY_TRACKER.md`
- `ARCHITECTURE_PLAN.md`
- `rbi_agent/` - All status/planning docs (keep only core code)

### Old Bot Files (After Refactor)
- `llm_agent/bot_llm.py`
- `lighter_agent/bot_lighter.py`
- `llm_agent/execution/trade_executor.py`
- `lighter_agent/execution/lighter_executor.py`

## Files to Keep But Simplify

### Core (Keep)
- `llm_agent/llm/` - LLM logic (use in strategy)
- `llm_agent/data/` - Data fetching (use in adapters)
- `trade_tracker.py` - Update for unified system
- `config.py` - Simplify

### Docs (Keep, Update)
- `README.md` - Update with new structure
- `PROGRESS.md` - Keep for tracking
- `AGENTS.md` - Keep for collaboration
- `REPOSITORY_STRUCTURE.md` - Update after refactor
- `USER_REFERENCE.md` - Keep user notes

## Files to Delete (Not Needed)

- `docs/composer_agent/` - Old audit docs
- `docs/` - Most planning docs (keep only essential)
- `research/` - Old research (archive if valuable)

## Structure After Cleanup

```
core/                    # NEW: Unified bot core
dexes/                   # KEEP: DEX-specific adapters
strategies/              # NEW: Strategy system
bots/                    # NEW: Thin bot wrappers
llm_agent/llm/          # KEEP: LLM logic (used by strategy)
llm_agent/data/         # KEEP: Data fetching (used by adapters)
trade_tracker.py        # KEEP: Update for unified
config.py               # KEEP: Simplify
logs/                   # KEEP: Logs
archive/                # KEEP: Old files
```


