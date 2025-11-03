# AGENTS.md - AI Agent Collaboration Guide

**Purpose**: This file helps AI agents collaborating on this codebase understand each other's roles, capabilities, and preferred interaction patterns.

---

## 🤖 Current Active Agents

### Composer (Current Agent)
**Model**: Claude Sonnet (via Cursor)
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

**Contact**: Via Cursor chat interface

---

## 📁 Key Directories for Agents

### Live Production Code (DO NOT MODIFY WITHOUT EXPLICIT PERMISSION)
- `llm_agent/` - Main LLM trading bot (RUNNING LIVE)
- `llm_agent/bot_llm.py` - Main bot orchestrator
- `llm_agent/llm/trading_agent.py` - Core decision engine
- `llm_agent/execution/trade_executor.py` - Trade execution
- `llm_agent/data/` - Data pipeline (all files)

### Experimental/New Features (Safe to Modify)
- `research/` - Research findings and experiments
- `scripts/` - Utility scripts
- `docs/` - Documentation

### Configuration (Caution Required)
- `config.py` - Global configuration (affects live bot)
- `.env` - Environment variables (NEVER commit)

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

**Live Bot**: Running with PID tracking (check `PROGRESS.md`)
**Main Bot File**: `llm_agent/bot_llm.py`
**Active Prompt**: v4 (see `llm_agent/prompts_archive/`)
**Trading Mode**: LIVE (real trades)

**Recent Changes**:
- Account balance now shown to LLM
- Position sizing increased (no hard caps)
- Max positions: 15
- Multi-token decision making (7 tokens analyzed)

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

---

**Last Updated**: 2025-11-01
**Maintained By**: Composer (Claude Sonnet via Cursor)

