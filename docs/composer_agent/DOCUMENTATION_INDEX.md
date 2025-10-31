# Documentation Index & Quick Reference

**Last Updated**: 2025-10-31  
**Purpose**: Quick navigation to all documentation

---

## 📋 Core Documents

### Audit & Planning
- **`AUDIT_REPORT.md`** - Comprehensive repository audit, findings, and recommendations
- **`docs/MULTI_BOT_ARCHITECTURE.md`** - Full design for multi-bot system with prompt templates

### User Guides
- **`USER_REFERENCE.md`** - Quick commands for daily use
- **`docs/PROMPT_CUSTOMIZATION.md`** - How to customize trading prompts

### Development
- **`CLAUDE.md`** - Development guide for Claude Code
- **`REPOSITORY_STRUCTURE.md`** - Complete repository map

---

## 🎯 Key Requirements Documented

### 1. Multi-Timeframe Macro Context
**Problem**: Macro context focuses on long-term trends (BTC dominance "high for months"), not actionable for swing trading.

**Solution**: 
- Daily context: Events TODAY, 24h BTC dominance changes, volume spikes
- Weekly context: Events THIS WEEK, 7-day trends, momentum
- Long-term: Background only (not actionable)

**See**: `docs/MULTI_BOT_ARCHITECTURE.md` Section 1

### 2. Prompt Template System
**Problem**: Prompts hardcoded in Python, hard to customize.

**Solution**:
- Markdown template files in `llm_agent/prompts/`
- Easy editing without code changes
- Variable substitution
- Multiple strategy templates

**See**: `docs/MULTI_BOT_ARCHITECTURE.md` Section 2

### 3. Multi-Bot Architecture
**Problem**: Can only run one bot with one strategy.

**Solution**:
- Run multiple bots simultaneously
- Each bot uses different prompt template
- Independent position limits per bot
- Config files for easy management

**See**: `docs/MULTI_BOT_ARCHITECTURE.md` Section 3

---

## 📁 File Locations

### Audit & Planning
```
AUDIT_REPORT.md                          # Main audit document
docs/MULTI_BOT_ARCHITECTURE.md          # Multi-bot design
docs/PROMPT_CUSTOMIZATION.md            # Prompt customization guide
```

### User Reference
```
USER_REFERENCE.md                        # Quick commands
```

### Development
```
CLAUDE.md                                # Dev guide
REPOSITORY_STRUCTURE.md                  # Repo structure
```

---

## 🚀 Implementation Status

### ✅ Documented (Ready for Dev Agent)
- Multi-timeframe macro context design
- Prompt template system design
- Multi-bot architecture design
- Implementation plan with phases

### ⏳ Pending Implementation
- Multi-timeframe macro context code
- Prompt template system code
- Multi-bot config system code
- Docker deployment with multi-bot support

---

## 📖 Quick Navigation

### "I want to..."
- **...understand the audit findings**: Read `AUDIT_REPORT.md`
- **...understand multi-bot design**: Read `docs/MULTI_BOT_ARCHITECTURE.md`
- **...customize prompts**: Read `docs/PROMPT_CUSTOMIZATION.md`
- **...run quick commands**: Read `USER_REFERENCE.md`
- **...understand repo structure**: Read `REPOSITORY_STRUCTURE.md`
- **...develop features**: Read `CLAUDE.md`

---

## 🔄 Related Documents

Each document references others:
- `AUDIT_REPORT.md` → References `docs/MULTI_BOT_ARCHITECTURE.md`
- `docs/PROMPT_CUSTOMIZATION.md` → References `docs/MULTI_BOT_ARCHITECTURE.md`
- `docs/MULTI_BOT_ARCHITECTURE.md` → Self-contained design document

---

**End of Documentation Index**

