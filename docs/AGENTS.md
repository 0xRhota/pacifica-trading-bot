# AGENTS.md - AI Agent Collaboration Guide

**Purpose**: This file helps AI agents collaborating on this codebase understand each other's roles, capabilities, and preferred interaction patterns.

---

## 📋 Quick Links

- **System Architecture**: [`ARCHITECTURE.md`](ARCHITECTURE.md) - Complete system design and structure
- **Development Guide**: [`CLAUDE.md`](CLAUDE.md) - For Claude Code development
- **User Commands**: [`USER_REFERENCE.md`](USER_REFERENCE.md) - For human operator

---

## 🤖 Current Active Agents

### Claude Code (Primary Agent)
**Model**: Claude Sonnet 4.5
**Role**: Primary development agent, code implementation, debugging
**Specialties**:
- Code implementation and refactoring
- Deep codebase analysis
- Repository organization
- Documentation
- Bug fixes and optimizations

**Preferences**:
- Document everything thoroughly
- Don't modify live working code without explicit permission
- Create new files/modules for experimental features
- Maintain clean repository organization

**Contact**: Via Claude Code interface

---

## 🏗️ System Overview

**See [`ARCHITECTURE.md`](ARCHITECTURE.md) for complete details**

### Two Active Bots
1. **Lighter Bot** (`lighter_agent/`) - zkSync, 101+ markets, zero fees
2. **Pacifica Bot** (`pacifica_agent/`) - Solana, 4-5 liquid markets

### Shared Infrastructure
- `llm_agent/llm/` - **SHARED** LLM decision engine
- `llm_agent/data/` - **SHARED** Market data & indicators
- `dexes/` - Exchange SDKs
- `config.py` - **SHARED** Global configuration
- `trade_tracker.py` - **SHARED** Trade logging

### Key Directories
- `research/` - All research findings (organized by topic)
- `scripts/` - Utility scripts (testing, debugging)
- `docs/` - API documentation and guides
- `logs/` - Log files (gitignored)
- `archive/` - Deprecated code (timestamped)

---

## 🚨 Critical Rules for All Agents

1. **Live Code Protection**: Never modify files in `llm_agent/` without explicit user permission
2. **Documentation First**: Always document new features thoroughly
3. **Test Before Deploy**: Run tests/manual verification before suggesting code changes
4. **Repository Organization**: Follow existing patterns, update REPOSITORY_STRUCTURE.md when adding new files
5. **Ask Before Breaking**: If unsure about impact, ask user or check PROGRESS.md first

---

## 📚 Documentation Standards

### Required Documentation for New Features
1. **README or dedicated .md file** explaining the feature
2. **Code comments** for complex logic
3. **Update REPOSITORY_STRUCTURE.md** if adding new directories/files
4. **Update PROGRESS.md** if making significant changes

### Documentation Locations
- `docs/` - Comprehensive documentation
- `research/` - Research findings and analysis
- `README.md` - Project overview
- `CLAUDE.md` - Development guide for Claude agents
- `USER_REFERENCE.md` - User's personal notes

---

## 🔄 Common Workflows

### Adding a New Feature
1. Create new files in appropriate directory
2. Document the feature
3. Update REPOSITORY_STRUCTURE.md
4. Test thoroughly
5. Update PROGRESS.md with changes

### Fixing a Bug
1. Check logs first (`logs/llm_bot.log`)
2. Identify root cause
3. Fix in minimal way
4. Document the fix
5. Test before restarting bot

### Research/Experimentation
1. Create files in `research/` directory
2. Document findings
3. Don't modify live code
4. Present findings for user review

---

## 📊 Current Project Status

**Live Bots**:
- **Lighter Bot**: `lighter_agent/bot_lighter.py` - ✅ RUNNING with Deep42 multi-timeframe integration
- **Pacifica Bot**: `pacifica_agent/bot_pacifica.py` - Status depends on user

**Check Bot Status**:
```bash
pgrep -f "bot_lighter"    # Lighter bot PID
pgrep -f "bot_pacifica"   # Pacifica bot PID
```

**See [`ARCHITECTURE.md`](ARCHITECTURE.md) for complete bot details and commands**

---

## 🤝 Collaboration Patterns

### When Taking Over from Another Agent
1. Read PROGRESS.md for recent changes
2. Check logs for current bot status
3. Review USER_REFERENCE.md for user preferences
4. Check REPOSITORY_STRUCTURE.md for file locations

### When Handing Off to Another Agent
1. Document all changes in PROGRESS.md
2. Update REPOSITORY_STRUCTURE.md if files changed
3. Note any issues or TODOs
4. Include relevant context in handoff message

---

## 🎯 Project Goals

1. **Increase Trading Volume & Sharpe Ratio** - For airdrop farming
2. **Bot Intelligence** - Make bot smarter, more autonomous
3. **Strategy Discovery** - Automated strategy backtesting (RBI agent)
4. **Multi-Bot Architecture** - Run multiple bots with different strategies
5. **Prompt Customization** - Easy prompt swapping without code changes

---

## 📝 Notes for Future Agents

- User values **repository organization** highly
- Prefers **documentation** over code comments
- Wants **easy prompt customization** without code changes
- Bot is currently **live trading** - be careful
- User is experimenting with **increasing bot freedom/intelligence**
- User strongly opposes hard-coded rules - wants metrics-driven decisions
- User needs high trade volume for points farming (can't drastically reduce frequency)

**Last Updated**: 2025-11-10 (Confidence-Based Holds + Performance Analysis)
**Maintained By**: Claude Code (Sonnet 4.5)

---

## 🆕 Recent Updates

### 2025-11-10: Confidence-Based Hold Logic + Performance Analysis 🎯

**Problem**: Lighter bot closing high-confidence positions too early to chase new setups

**Solution**: Implemented confidence-based hold requirements
- **High confidence (≥0.7)**: Minimum 2 hour hold
- **Low confidence (<0.7)**: Can close early
- Confidence now tracked in `trade_tracker.py`

**Files Modified**:
- `trade_tracker.py` - Added confidence field to TradeEntry
- `lighter_agent/execution/lighter_executor.py` - Added hold logic to `_close_position()`

**Performance Analysis**:
- Created `research/lighter/LIGHTER_SUCCESS_ANALYSIS_NOV10.md`
- Analyzed 1,009 closed trades from CSV export
- Key Finding: Recent 20 trades show 60% WR (vs 47.3% overall) - strategy improving!
- Top performers: HBAR (100% WR), BTC (88.9% WR), UNI (76.9% WR)

**Repository Organization**:
- ✅ Analysis reports: `research/lighter/`
- ✅ CSV exports: `logs/trades/` (with JSON trade data)
- ✅ Bot status: `docs/BOT_STATUS.md`
- All files now follow existing patterns

---

### 2025-11-07: Pacifica Account Balance Integration 💰

**Problem**: Bot was hardcoded to use `account_balance = 0.0`, not fetching real balance from API
**User Request**: "ONLY DATA direct from API pls. youre hallucinating or using bad data"

**Investigation**:
- Found `/account` endpoint returns full account data (balance, equity, margin used, etc.)
- `PacificaSDK` class didn't have `get_balance()` method (marked as "doesn't exist")
- Bot was passing 0.0 to executor and LLM instead of real $113.75 equity

**Fixes Applied**:
1. **Added `get_balance()` to PacificaSDK** (dexes/pacifica/pacifica_sdk.py:210-231)
   - Calls `/account?account={address}` endpoint
   - Returns full account data: balance, equity, available_to_spend, margin_used

2. **Enabled balance tracking in bot** (pacifica_agent/bot_pacifica.py:309-321)
   - Fetches account equity every decision cycle
   - Logs: `💰 Account equity: $113.75 | Available: $106.26`
   - Uses account_equity (balance + unrealized P&L) not just balance

3. **Updated executor to fetch balance** (pacifica_agent/execution/pacifica_executor.py:57-68)
   - Now returns real account_equity for dynamic position sizing
   - Falls back to None if API unavailable (executor has fallback logic)

**API Data Retrieved** (YOUR_ACCOUNT_PUBKEY):
- Account Equity: $113.75
- Balance: $113.67
- Available to Spend: $106.26
- Margin Used: $7.49
- Open Positions: 1

**Documentation Created**:
- `research/pacifica/ACCOUNT_SUMMARY.md` - Real API account data
- `research/pacifica/CSV_ANALYSIS_WARNING.md` - Moved and marked CSV analysis with warning

**User Philosophy**:
- No hard-coded rules (e.g., minimum hold times)
- Want intelligent system that uses metrics to make decisions
- Need volume for points farming, can't reduce trade frequency drastically
- "we want an intelligent system" that adapts based on data

**Status**: ✅ Complete - Bot ready for restart to enable balance tracking

**Files Modified**:
- `dexes/pacifica/pacifica_sdk.py` - Added get_balance() method
- `pacifica_agent/bot_pacifica.py` - Enabled balance fetching
- `pacifica_agent/execution/pacifica_executor.py` - Updated _fetch_account_balance()

---


