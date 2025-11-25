# TODO - Pacifica Trading Bot

## 🚀 Priority: Hetzner Server Deployment

### Phase 1: Security Setup (One-Time)
- [ ] Generate SSH key on local machine
- [ ] Provision Hetzner CPX31 server (Choose location: Germany or USA)
- [ ] Add SSH public key to server
- [ ] Test SSH connection (no password)
- [ ] Create non-root user with sudo access
- [ ] Install fail2ban (auto-ban brute force attempts)
- [ ] Configure firewall (only SSH port 22)
- [ ] Disable password login (keys only)

### Phase 2: Deploy Lighter Bot
- [ ] SSH into server
- [ ] Install Python 3.11+ environment
- [ ] Install git
- [ ] Clone repository to server
- [ ] Transfer .env file securely via SCP
- [ ] Set .env permissions (chmod 600)
- [ ] Install Python dependencies (pip install -r requirements.txt)
- [ ] Create systemd service file for lighter-bot
- [ ] Enable and start lighter-bot service
- [ ] Test: Verify bot runs 24/7
- [ ] Test: Verify auto-restart on crash
- [ ] Configure Claude SSH access for remote control

### Phase 3: Operations & Monitoring
- [ ] Document SSH commands for daily operations
- [ ] Set up log monitoring
- [ ] Test restart commands via Claude
- [ ] Create backup/restore procedure for .env
- [ ] Document process for adding future bots

---

## 🧠 Self-Analysis & Memory System

### Phase 1: Analysis Script (Semi-Automated)
- [ ] Create `scripts/analyze_bot_performance.py`
  - [ ] Load Lighter CSV export (from logs/trades/)
  - [ ] Parse trade data (wins, losses, confidence, symbols)
  - [ ] Calculate performance metrics (win rate, avg PnL, trends)
  - [ ] LLM analysis: Identify winning/losing patterns
  - [ ] Generate insights JSON with actionable patterns
  - [ ] Cross-reference with trade_tracker.json for sync

### Phase 2: Memory System
- [ ] Create `llm_agent/memory/` directory
- [ ] Create `llm_agent/memory/trading_insights.json` structure
- [ ] Define memory schema (patterns, win rates, actions, confidence scores)
- [ ] Add version control for memory file

### Phase 3: Bot Integration
- [ ] Update bot prompt to load memory file
- [ ] Integrate insights into decision-making context
- [ ] Add memory age check (warn if >7 days old)
- [ ] Test: Verify bot uses insights in decisions
- [ ] Log when bot follows/ignores memory patterns

### Phase 4: Automation (Future)
- [ ] Create manual trigger: "analyze lighter bot performance"
- [ ] Test semi-automated analysis workflow
- [ ] Consider: Upgrade to weekly automated analysis (cron job)
- [ ] Consider: Monthly deep dive reviews

---

## 📊 Data Sync & Quality

### CSV Export Process
- [ ] Document Lighter CSV export process
- [ ] Create standard location: logs/trades/
- [ ] Add CSV parsing to analysis script
- [ ] Cross-reference CSV with trade_tracker.json
- [ ] Sync any missing data between sources

---

## 🔮 Future Enhancements

### Multi-Bot Scaling (Post-Hetzner)
- [ ] Deploy bot #2 to Hetzner (systemd service)
- [ ] Deploy bot #3 to Hetzner (systemd service)
- [ ] Test: Multiple bots running simultaneously
- [ ] Monitor resource usage (CPU, RAM)

### Advanced Monitoring (Optional)
- [ ] Consider: FastAPI control endpoint
- [ ] Consider: Grafana dashboards
- [ ] Consider: Web UI for bot management

---

**Last Updated**: 2025-11-10
**Status**: Planning phase - ready to start implementation
