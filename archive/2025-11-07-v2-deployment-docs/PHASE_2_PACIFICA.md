# PHASE 2: Pacifica Bot Migration Plan

## 🎯 Mission
Transfer all Lighter bot improvements to Pacifica bot for dual airdrop farming.

## Current Status

### Lighter Bot (PHASE 1 - Active)
**Location**: `lighter_agent/`
**Status**: ✅ Working, optimized, generating volume
**Features**:
- Dynamic symbol loading (101+ markets from API)
- AI-driven decisions (DeepSeek Chat)
- Comprehensive logging (every step visible)
- Zero hardcoded symbols
- Zero fees on Lighter DEX

### Pacifica Bot (PHASE 2 - Paused)
**Location**: `pacifica/` (entire framework)
**Status**: ⚠️ Working but needs modernization
**Issues**:
- Separate framework (not using shared llm_agent modules)
- May have hardcoded symbols (need to check)
- Duplicate infrastructure (own trade tracker, etc.)

---

## Migration Strategy

### Option A: Refactor Pacifica Framework (Recommended)
**Goal**: Make Pacifica use same pattern as Lighter

**Steps**:
1. Create `pacifica_agent/` (mirror of lighter_agent/)
2. Reuse shared modules:
   - `llm_agent/llm/` (LLM decisions)
   - `llm_agent/data/` (indicators, macro, OI)
   - `trade_tracker.py` (root level)
3. Create Pacifica-specific modules:
   - `pacifica_agent/data/pacifica_fetcher.py` (OHLCV from Pacifica API)
   - `pacifica_agent/data/pacifica_aggregator.py` (data aggregation)
   - `pacifica_agent/execution/pacifica_executor.py` (trade execution)
   - `pacifica_agent/bot_pacifica.py` (main loop)
4. Port improvements from lighter_agent:
   - Dynamic symbol loading
   - Comprehensive logging
   - Same decision validation logic
5. Archive old `pacifica/` framework

**Result**: Consistent pattern for both DEXs, shared AI brain, DEX-specific execution

### Option B: Minimal Fixes to Existing Pacifica
**Goal**: Just get it working with minimal changes

**Steps**:
1. Keep `pacifica/` as-is
2. Update to use shared `llm_agent/llm/` (if not already)
3. Fix any hardcoded symbols
4. Improve logging to match Lighter bot
5. Test and redeploy

**Result**: Faster, but maintains duplicate infrastructure

---

## Recommended Approach: **Option A** (Clean Refactor)

**Why**:
- Both bots use same AI brain (consistency)
- Easier to maintain (one pattern, not two)
- Easier to add more DEXs later
- Cleaner mental model

**Timeline**:
1. **After Lighter bot is perfected** (wait until confident)
2. Create `pacifica_agent/` using Lighter as template
3. Test in dry-run mode
4. Deploy for Pacifica airdrop farming
5. Archive old `pacifica/` framework

---

## What to Preserve from Current Pacifica

### ✅ Keep (Valuable Code)
- `pacifica/dexes/pacifica/sdk.py` - Pacifica API wrapper
- `pacifica/dexes/pacifica/api.py` - API client
- Any Pacifica-specific logic in old bot

### ❌ Replace (Duplicates)
- `pacifica/core/trade_tracker.py` → Use root `trade_tracker.py`
- `pacifica/core/risk_manager.py` → Use shared risk logic
- `pacifica/strategies/` → Use shared `llm_agent/llm/`
- `pacifica/utils/` → Consolidate into shared modules

---

## Checklist for Phase 2 Kickoff

**Before Starting**:
- [ ] Lighter bot running stably for 1+ week
- [ ] No critical bugs in Lighter bot
- [ ] Confident in current architecture
- [ ] Ready to dedicate time to Pacifica migration

**During Migration**:
- [ ] Create `pacifica_agent/` directory structure
- [ ] Port Pacifica SDK to `dexes/pacifica/pacifica_sdk.py`
- [ ] Create pacifica_fetcher.py (mirror of lighter_fetcher.py)
- [ ] Create pacifica_aggregator.py (mirror of lighter_aggregator.py)
- [ ] Create pacifica_executor.py (mirror of lighter_executor.py)
- [ ] Create bot_pacifica.py (mirror of bot_lighter.py)
- [ ] Test in dry-run mode
- [ ] Deploy live for airdrop farming
- [ ] Archive old `pacifica/` framework

**After Migration**:
- [ ] Both bots using shared AI brain
- [ ] Consistent logging across both bots
- [ ] Easy to compare performance
- [ ] Ready to add more DEXs (e.g., Agent Lightning, Moon Dev backtesting)

---

## Future Vision: Multi-DEX Airdrop Farming

```
pacifica-trading-bot/
├─ 🤖 lighter_agent/         # Lighter DEX (101+ markets, zero fees)
├─ 🤖 pacifica_agent/        # Pacifica DEX (dual airdrop)
├─ 🤖 agent_lightning/       # Future: Agent Lightning
├─ 🤖 moon_dev_agent/        # Future: Moon Dev backtesting
│
├─ 🧠 llm_agent/             # SHARED AI BRAIN
│   ├─ data/                 # Indicators, macro, OI
│   └─ llm/                  # DeepSeek decisions
│
├─ 🔧 dexes/                 # DEX SDKs
│   ├─ lighter/lighter_sdk.py
│   ├─ pacifica/pacifica_sdk.py
│   └─ agent_lightning/...
│
└─ 🛠️ shared/
    ├─ trade_tracker.py      # Track all DEXs
    └─ config.py             # Global config
```

**End Goal**: One AI brain, multiple DEX arms, consistent airdrop farming across all exchanges.

---

## Notes
- Don't rush Phase 2 - Lighter bot must be rock solid first
- Use Lighter bot as template - it's the "golden copy"
- Keep this doc updated as Lighter bot evolves
- When ready for Phase 2, revisit this plan and adjust based on learnings
