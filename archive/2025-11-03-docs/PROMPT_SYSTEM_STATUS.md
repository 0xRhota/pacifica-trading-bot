# Prompt Experimentation System - Implementation Status

**Date**: 2025-10-31
**Status**: ✅ COMPLETE - Simple prompt swapping system implemented
**Purpose**: Allow easy prompt experimentation without building full multi-bot architecture

---

## What Was Implemented

### ✅ Simple Prompt Versioning System

**User Request**: "I just want to be able to experiment on the fly today, right? So we need a system where we can always revert or change. Simple, very simple, documented."

**Solution Delivered**:
1. Prompt archive with text files for each version
2. Swap script for one-command switching
3. Full documentation in multiple guides
4. Version tracking in PROGRESS.md
5. All organized and documented per standards

---

## File Locations & Organization

### 1. Prompt Archive
**Location**: `llm_agent/prompts_archive/`
**Files**:
- `v1_baseline_conservative.txt` - Original conservative prompt (baseline)
- `v2_aggressive_swing.txt` - Aggressive swing trading prompt (CURRENT)
- `README.md` - Quick guide in archive folder

**Purpose**: Store all prompt versions as plain text files for easy editing/swapping

### 2. Swap Script
**Location**: `scripts/swap_prompt.sh`
**Executable**: Yes (`chmod +x`)
**Usage**:
```bash
./scripts/swap_prompt.sh                    # List available versions
./scripts/swap_prompt.sh v1_baseline_conservative  # Swap to version
```

**What it does**:
- Reads prompt from archive text file
- Uses Python to replace instructions section in `llm_agent/llm/prompt_formatter.py` (lines 160-191)
- Shows restart commands after swapping

### 3. Documentation
**Root Level**:
- `PROMPT_EXPERIMENTS.md` - Complete guide for experimentation (NEW)
- `PROGRESS.md` - Updated with prompt version history (UPDATED)
- `USER_REFERENCE.md` - Updated with swap commands (UPDATED)
- `REPOSITORY_STRUCTURE.md` - Updated with new files (UPDATED)
- `PROMPT_SYSTEM_STATUS.md` - This file (NEW)

---

## Current Prompt Status

### Version 2 - Aggressive Swing Trading (ACTIVE)
**File**: `llm_agent/prompts_archive/v2_aggressive_swing.txt`
**Applied**: 2025-10-31 14:38
**Bot PID**: 93626

**Changes from v1**:
1. NOTHING trigger: "if unclear" → "ONLY if extremely uncertain - prefer action over inaction"
2. Added "SWING TRADING STRATEGY" section:
   - Focus on daily/weekly movements, not long-term trends
   - Look for 24h volume spikes >50%
   - Contrarian entries: Fear & Greed < 30 + RSI < 40 = LONG
   - Profit taking: Fear & Greed > 70 + RSI > 70 = SHORT
   - "Don't wait for perfect setups"
   - "Short-term volatility is opportunity, not risk"
   - "Small losses acceptable - goal is profitable trades"

**Goal**: Make bot more active, focus on swing trading timeframes

---

## How to Use (Simple Workflow)

### List Available Prompts
```bash
./scripts/swap_prompt.sh
```

### Swap to a Prompt
```bash
./scripts/swap_prompt.sh v1_baseline_conservative  # Conservative
./scripts/swap_prompt.sh v2_aggressive_swing       # Aggressive
```

### Restart Bot
```bash
pkill -f "llm_agent.bot_llm"
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

### Monitor Results
```bash
python3 scripts/view_decisions.py  # Quick summary
```

---

## Create New Prompt Version

### Step 1: Copy Existing
```bash
cp llm_agent/prompts_archive/v2_aggressive_swing.txt llm_agent/prompts_archive/v3_my_test.txt
```

### Step 2: Edit
```bash
nano llm_agent/prompts_archive/v3_my_test.txt
```

### Step 3: Swap and Test
```bash
./scripts/swap_prompt.sh v3_my_test
pkill -f "llm_agent.bot_llm"
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

### Step 4: Document in PROGRESS.md
Add entry under "Prompt Version History":
```markdown
### Version 3 - My Test (2025-10-31 HH:MM)
**Changes**: [What you changed]
**Goal**: [What you're testing]
**Bot PID**: [PID from restart]
```

---

## Revert Anytime

### Method 1: Swap Script
```bash
./scripts/swap_prompt.sh v1_baseline_conservative
pkill -f "llm_agent.bot_llm"
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

### Method 2: Git
```bash
git checkout llm_agent/llm/prompt_formatter.py
pkill -f "llm_agent.bot_llm"
nohup python3 -u -m llm_agent.bot_llm --live --interval 300 > logs/llm_bot.log 2>&1 &
```

---

## Documentation Standards Met

### ✅ Organization
- All prompt versions in dedicated archive folder
- Swap script in scripts/ directory (standard location)
- Clear separation of concerns

### ✅ Documentation
- `PROMPT_EXPERIMENTS.md` - Complete experimentation guide
- `PROGRESS.md` - Version history tracking
- `USER_REFERENCE.md` - Quick commands
- `REPOSITORY_STRUCTURE.md` - File locations documented
- Archive folder has own README.md

### ✅ Reversibility
- Easy revert with swap script
- Git fallback option
- All versions preserved as text files

### ✅ Simplicity
- One command to list versions
- One command to swap
- Plain text files (easy to edit)
- No complex build process

---

## What Was NOT Implemented (By Design)

### Multi-Bot Architecture
**Reason**: User wanted "simple, very simple" for today's experimentation
**Status**: Fully designed in other agent's docs, ready for future implementation
**Reference**: See `AUDIT_REPORT.md`, `MULTI_BOT_ARCHITECTURE.md`, `multi_bot_prompt_prd.txt`

### Multi-Timeframe Macro Context
**Reason**: User wanted quick prompt changes first, not data pipeline changes
**Status**: Fully designed, ready for future Phase 1 implementation
**Reference**: See `MULTI_BOT_ARCHITECTURE.md` Section 1

### Template System with Variables
**Reason**: User wanted to experiment NOW, not wait for template engine
**Status**: Fully designed, ready for future Phase 2 implementation
**Reference**: See `MULTI_BOT_ARCHITECTURE.md` Section 2

---

## Next Steps (User's Choice)

### Option 1: Continue Experimenting (Recommended for Today)
- Create v3, v4, v5 prompt variants
- Test each for 6-24 hours
- Document results in PROGRESS.md
- Find optimal prompt for current market conditions

### Option 2: Implement Multi-Timeframe Context (Phase 1)
- Modify `llm_agent/data/macro_fetcher.py`
- Add daily/weekly/long-term sections
- Make macro context actionable for swing trading
- See `MULTI_BOT_ARCHITECTURE.md` for full plan

### Option 3: Implement Template System (Phase 2)
- Create `llm_agent/prompts/` directory
- Extract prompts to markdown templates
- Add variable substitution
- See `MULTI_BOT_ARCHITECTURE.md` for full plan

### Option 4: Implement Multi-Bot Architecture (Phase 3)
- Create bot config system
- Support running multiple bots simultaneously
- Per-bot logging and position tracking
- See `MULTI_BOT_ARCHITECTURE.md` for full plan

---

## Summary for Other Agent

**What we did**:
- Implemented simple prompt versioning system (text files + swap script)
- User can now experiment with prompts easily and revert anytime
- Fully documented and organized per repository standards

**What we didn't do**:
- Multi-bot architecture (designed but not implemented)
- Multi-timeframe macro context (designed but not implemented)
- Template system with variables (designed but not implemented)

**Why**:
- User wanted "simple, very simple, documented" for TODAY
- User wanted to experiment on the fly, not wait for full architecture
- Full architecture is designed and ready in your docs when user is ready

**Current status**:
- Bot running with v2_aggressive_swing prompt (PID: 93626)
- User can swap prompts in seconds
- All changes tracked in PROGRESS.md
- Ready to experiment with v3, v4, v5 variants

---

**End of Status Document**
