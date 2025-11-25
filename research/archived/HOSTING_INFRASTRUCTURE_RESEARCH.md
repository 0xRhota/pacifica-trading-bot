# Trading Bot Hosting Infrastructure Research
**Date**: November 10, 2025
**Purpose**: Research optimal hosting for multiple perp DEX trading bots

---

## 🎯 Requirements Summary

**Goal**: Scale from local hosting to remote hosting for multiple perp DEX bots
- Run bots 24/7 without local machine dependency
- Access via web UI for monitoring/management
- Allow remote control (start/stop via Claude/API)
- Support multiple DEX integrations (Lighter, Hyperliquid, dYdX, Vertex, etc.)

---

## 📊 Hosting Provider Comparison

### 🏆 Recommended: Hetzner Cloud

**Best For**: Budget-conscious traders, European markets, simple deployment

**Pricing**:
- Starting: €2.49/month (~$2.70/month)
- Mid-tier: €20-40/month (~$22-44/month) for robust setup
- **Cost**: 10-100x cheaper than AWS for similar specs

**Pros**:
- ✅ Best price/performance ratio
- ✅ Simple, clean interface
- ✅ Good European latency (Germany, Finland datacenters)
- ✅ NVMe storage (7x faster than SATA SSD)
- ✅ Python API available (`hcloud-python`)
- ✅ Suitable for most crypto trading needs

**Cons**:
- ❌ Limited advanced features vs AWS
- ❌ No formal SLA guarantees
- ❌ Primarily European (Germany, Finland, USA, Singapore)
- ❌ Higher latency to Asian exchanges

**Recommended Specs for Multi-Bot Setup**:
- **CPX31**: 4 vCPU, 8GB RAM, 160GB NVMe - €17.17/month (~$19/month)
  - Ideal for running 5-10 bots simultaneously
  - Enough resources for Python bots + monitoring

**Data Centers**:
- Germany (Falkenstein, Nuremberg, Helsinki) - Best for European DEXs
- USA (Ashburn, Virginia) - Best for US-based exchanges
- Singapore - Best for Asian exchanges (if available)

---

### 🥈 Runner-Up: DigitalOcean

**Best For**: Global coverage, ease of use, balanced features

**Pricing**:
- Starting: ~$4-6/month (basic droplet)
- Mid-tier: ~$48-96/month for production-ready setup
- **Cost**: ~7x cheaper than AWS, but 2-3x more than Hetzner

**Pros**:
- ✅ Clean, user-friendly interface
- ✅ One-click deployments
- ✅ 99.99% uptime SLA
- ✅ 24/7 support
- ✅ Better global coverage than Hetzner
- ✅ Extensive documentation
- ✅ Good API and CLI tools

**Cons**:
- ❌ More expensive than Hetzner
- ❌ Still lacks some AWS advanced features
- ❌ Not as cost-effective for simple use cases

**Recommended Specs**:
- **General Purpose Droplet**: 4 vCPU, 8GB RAM - $48/month

---

### 💰 AWS (Overkill for Most Traders)

**Best For**: Enterprise scale, extreme reliability requirements, complex architectures

**Pricing**:
- Starting: ~$100/month minimum
- Typical: $500-1000+/month with scaling
- **Cost**: 10-100x more expensive than Hetzner

**Pros**:
- ✅ Most extensive global coverage
- ✅ Closest to exchange servers (lowest latency possible)
- ✅ 99.99% SLA with redundancy
- ✅ Unlimited scaling
- ✅ Advanced features (Lambda, ECS, etc.)

**Cons**:
- ❌ Expensive (overkill for individual traders)
- ❌ Complex pricing model
- ❌ Steeper learning curve
- ❌ Can get very expensive quickly

**When to Use**: Only if you need institutional-grade infrastructure or co-location with major exchanges.

---

## 🌍 Latency Considerations

### Critical Latency Benchmarks

**Target Latencies**:
- **Sub-10ms**: Same datacenter/region as exchange (ideal for HFT)
- **20-50ms**: Continental connections (acceptable for most strategies)
- **100-200ms**: Transcontinental (too high for competitive strategies)

### Geographic Recommendations

**For Lighter DEX (zkSync)**:
- zkSync validators distributed globally
- **Recommendation**: US East (Ashburn) or EU (Frankfurt/Germany)

**For Hyperliquid**:
- Order-book DEX requires low latency
- **Recommendation**: US-based VPS (East Coast preferred)

**For dYdX v4**:
- Cosmos-based chain, distributed validators
- Can handle 1500 orders/second
- **Recommendation**: Run own validator node OR US/EU VPS

**For GMX/Vertex (Arbitrum)**:
- Arbitrum nodes
- **Recommendation**: US-based VPS with good Arbitrum node access

### Provider Location Summary

| Provider | Best Regions | Asian Access | US Access | EU Access |
|----------|-------------|--------------|-----------|-----------|
| **Hetzner** | EU (Germany/Finland) | ❌ Limited | ⚠️ OK (Virginia) | ✅ Excellent |
| **DigitalOcean** | Global | ✅ Good | ✅ Good | ✅ Good |
| **AWS** | Global | ✅ Excellent | ✅ Excellent | ✅ Excellent |

---

## 🤖 Perp DEX API Support Analysis

### 🏆 Tier 1: Best API/Bot Support

#### Hyperliquid
- **Order Type**: Order-book DEX
- **API Maturity**: ⭐⭐⭐⭐⭐ Excellent
- **Bot Support**: Python SDK, REST + WebSocket
- **Best For**: Advanced programmatic trading, HFT
- **Latency Critical**: Yes (order-book)
- **Infrastructure**: RPC node providers available (Chainstack, Dwellir, dRPC)
- **Notes**: Microsecond-level control, unified chain with HyperCore (trading) + HyperEVM (smart contracts)

#### dYdX v4
- **Order Type**: Order-book DEX
- **API Maturity**: ⭐⭐⭐⭐⭐ Excellent
- **Bot Support**: Python, TypeScript, Rust SDKs
- **Best For**: Programmatic trading, HFT, advanced order types
- **Latency Critical**: Yes (can process 1500 orders/second)
- **Infrastructure**: Can run own validator node for zero latency
- **Notes**: Most mature DEX for institutional-grade bot trading, supports short-term orders (low latency) and stateful orders (retail)

### 🥈 Tier 2: Good API Support

#### Vertex Protocol
- **Order Type**: Hybrid (order-book + AMM)
- **API Maturity**: ⭐⭐⭐⭐ Good
- **Bot Support**: Python SDK, Hummingbot integration
- **Best For**: Unified spot + perps + money market
- **Latency Critical**: Moderate
- **Infrastructure**: Arbitrum-based
- **Notes**: Good for multi-market strategies (spot/perp/lending combined)

#### Lighter (Current Bot)
- **Order Type**: Order-book DEX
- **API Maturity**: ⭐⭐⭐⭐ Good
- **Bot Support**: REST API (your bot uses this)
- **Best For**: Zero-fee trading, zkSync ecosystem
- **Latency Critical**: Yes (order-book)
- **Infrastructure**: zkSync validators
- **Notes**: Already running successfully, zero fees

### 🥉 Tier 3: Basic API Support

#### GMX
- **Order Type**: AMM/GLP pool
- **API Maturity**: ⭐⭐⭐ Moderate
- **Bot Support**: CCXT integration (via Arbitrum grant)
- **Best For**: Simple strategies, predictable flows
- **Latency Critical**: No (AMM model)
- **Infrastructure**: Arbitrum-based
- **Notes**: Less suited for advanced programmatic trading vs order-book DEXs

---

## 🛠️ Technical Infrastructure Requirements

### Server Specifications (Multi-Bot Setup)

**Minimum (2-3 bots)**:
- 2 vCPU
- 4GB RAM
- 80GB NVMe SSD
- 1Gbps network
- **Cost**: ~€10/month (Hetzner)

**Recommended (5-10 bots)**:
- 4 vCPU
- 8GB RAM
- 160GB NVMe SSD
- 1Gbps network
- **Cost**: ~€17-20/month (Hetzner CPX31)

**Heavy (10+ bots + monitoring)**:
- 8 vCPU
- 16GB RAM
- 320GB NVMe SSD
- 1Gbps network
- **Cost**: ~€35-45/month (Hetzner CPX41)

### Software Stack

**Operating System**: Ubuntu 22.04 LTS (most common, well-documented)

**Core Requirements**:
- Python 3.11+
- systemd (for service management)
- nginx (reverse proxy for web UI)
- PostgreSQL or SQLite (trade logging)
- Redis (optional, for caching)

**Monitoring/Management**:
- Grafana + Prometheus (metrics/dashboards)
- Uptime Kuma (uptime monitoring)
- Portainer (if using Docker)
- tmux/screen (session management)

**Remote Access**:
- SSH (always)
- Web UI (Grafana for monitoring)
- API endpoint (for Claude to control bots)

---

## 🔐 Security Considerations

### Essential Security Measures

1. **SSH Key Authentication**: Disable password auth
2. **Firewall**: UFW or iptables (only open necessary ports)
3. **Fail2ban**: Prevent brute force attacks
4. **API Key Rotation**: Regular rotation of exchange API keys
5. **Environment Variables**: Never commit `.env` files
6. **Encrypted Backups**: Regular backups of trade data
7. **2FA on VPS**: If provider supports it
8. **Rate Limiting**: On any exposed API endpoints

---

## 🎛️ Management & Access Options

### 1. Web-Based Management

**Grafana Dashboard** (Recommended):
- Real-time bot monitoring
- Performance metrics
- Trade history visualization
- Alert configuration
- Access from anywhere via HTTPS

**Portainer** (If using Docker):
- Container management UI
- Start/stop/restart containers
- View logs in real-time
- Resource monitoring

### 2. API-Based Control

**Custom FastAPI Endpoint**:
```python
# Create simple API for bot control
from fastapi import FastAPI

app = FastAPI()

@app.post("/bots/{bot_name}/start")
def start_bot(bot_name: str):
    # Start systemd service
    subprocess.run(["systemctl", "start", f"{bot_name}.service"])
    return {"status": "started"}

@app.post("/bots/{bot_name}/stop")
def stop_bot(bot_name: str):
    subprocess.run(["systemctl", "stop", f"{bot_name}.service"])
    return {"status": "stopped"}
```

**Benefits**:
- Claude can call API to control bots
- User can control via curl/Postman
- Easy to integrate with Telegram bot

### 3. systemd Services

**Standard Linux Service Management**:
```bash
# Start/stop/restart bots
sudo systemctl start lighter_bot
sudo systemctl stop pacifica_bot
sudo systemctl restart hyperliquid_bot

# View status
sudo systemctl status *_bot

# View logs
journalctl -u lighter_bot -f
```

**Benefits**:
- Automatic restart on crash
- Boot on server startup
- Standard Linux tooling

---

## 💡 Recommended Setup Architecture

### Option A: Simple Multi-Bot Setup (Recommended)

```
┌─────────────────────────────────────────┐
│      Hetzner Cloud VPS (CPX31)          │
│         4 vCPU, 8GB RAM, €17/mo         │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │ Lighter  │  │ Pacifica │            │
│  │   Bot    │  │   Bot    │            │
│  │(systemd) │  │(systemd) │            │
│  └──────────┘  └──────────┘            │
│                                         │
│  ┌──────────┐  ┌──────────┐            │
│  │Hyperlqd  │  │ dYdX Bot │            │
│  │  Bot     │  │          │            │
│  │(systemd) │  │(systemd) │            │
│  └──────────┘  └──────────┘            │
│                                         │
│  ┌─────────────────────────┐           │
│  │   Grafana Dashboard     │           │
│  │   (Port 3000, HTTPS)    │           │
│  └─────────────────────────┘           │
│                                         │
│  ┌─────────────────────────┐           │
│  │  FastAPI Control API    │           │
│  │  (Port 8000, Auth)      │           │
│  └─────────────────────────┘           │
│                                         │
│  PostgreSQL (Trade Logs)                │
│  Redis (Caching)                        │
└─────────────────────────────────────────┘
```

**Access**:
- SSH: User + Claude (via terminal)
- Grafana: https://your-vps-ip:3000 (monitoring)
- Control API: https://your-vps-ip:8000/docs (bot control)

---

### Option B: Docker-Based Setup (More Complex)

```
┌─────────────────────────────────────────┐
│      Hetzner Cloud VPS (CPX31)          │
├─────────────────────────────────────────┤
│                                         │
│        Docker + Docker Compose          │
│                                         │
│  ┌────────────────────────────────────┐│
│  │  Bot Containers (auto-restart)     ││
│  │  - lighter_bot                     ││
│  │  - pacifica_bot                    ││
│  │  - hyperliquid_bot                 ││
│  │  - dydx_bot                        ││
│  └────────────────────────────────────┘│
│                                         │
│  ┌────────────────────────────────────┐│
│  │  Management Stack                  ││
│  │  - Portainer (container mgmt)     ││
│  │  - Grafana (monitoring)           ││
│  │  - Prometheus (metrics)           ││
│  └────────────────────────────────────┘│
│                                         │
│  PostgreSQL Container                   │
│  Redis Container                        │
└─────────────────────────────────────────┘
```

**Pros**:
- Easier to scale/replicate
- Better isolation
- Portable (can move between providers)

**Cons**:
- More complex setup
- Slightly higher overhead

---

## 🚀 Recommended Implementation Plan

### Phase 1: Single VPS Setup (Week 1)

1. **Provision Hetzner VPS** (CPX31, Germany or USA)
   - €17/month, 4 vCPU, 8GB RAM
   - Ubuntu 22.04 LTS

2. **Basic Security Setup**
   - SSH key authentication
   - UFW firewall
   - Fail2ban
   - Automatic security updates

3. **Migrate Existing Bots**
   - Deploy lighter_agent (already working)
   - Deploy pacifica_agent (already working)
   - Set up as systemd services
   - Test for 24-48 hours

4. **Basic Monitoring**
   - Set up log rotation
   - Configure trade_tracker.py to use PostgreSQL
   - Simple uptime monitoring

**Cost**: €17/month (~$19/month)

---

### Phase 2: Management UI (Week 2)

1. **Deploy Grafana**
   - Install and configure
   - Create dashboards for:
     - Bot uptime
     - Trade performance
     - P&L tracking
     - Position monitoring
   - Set up HTTPS with Let's Encrypt

2. **Control API**
   - Simple FastAPI endpoint
   - Start/stop/restart endpoints
   - Status endpoints
   - Authentication (API key)

3. **Documentation**
   - API documentation
   - Dashboard guides
   - Emergency procedures

**Additional Cost**: None (same VPS)

---

### Phase 3: Scale to Multiple DEXs (Week 3-4)

1. **Research & Integrate New DEXs**
   - Hyperliquid (order-book, best API)
   - dYdX v4 (order-book, institutional-grade)
   - Vertex (hybrid, multi-market)

2. **Adapt Bot Code**
   - Extract shared LLM logic (already done with lighter_agent/pacifica_agent)
   - Create new exchange adapters
   - Test in dry-run mode

3. **Deploy New Bots**
   - Add as systemd services
   - Update monitoring dashboards
   - Update control API

**Additional Cost**: May need to upgrade to CPX41 (€35/month) for 8+ bots

---

## 📋 Next Steps Checklist

### Immediate (Do First)
- [ ] Create Hetzner Cloud account
- [ ] Provision CPX31 VPS in preferred region (Germany or USA East)
- [ ] Set up SSH key authentication
- [ ] Basic firewall configuration

### Week 1
- [ ] Deploy lighter_agent to VPS
- [ ] Deploy pacifica_agent to VPS
- [ ] Set up systemd services
- [ ] Configure log rotation
- [ ] Test bots for 24-48 hours

### Week 2
- [ ] Install and configure Grafana
- [ ] Create monitoring dashboards
- [ ] Build simple control API (FastAPI)
- [ ] Set up HTTPS with Let's Encrypt
- [ ] Document access methods

### Week 3+
- [ ] Research Hyperliquid integration
- [ ] Research dYdX v4 integration
- [ ] Create DEX adapter pattern
- [ ] Deploy additional bots
- [ ] Scale VPS if needed

---

## 💰 Cost Summary

### Budget Option (Current Setup)
- **Provider**: Hetzner CPX31
- **Cost**: €17/month (~$19/month)
- **Capacity**: 5-10 bots comfortably
- **Total First Year**: ~$228/year

### Growth Option (10+ bots)
- **Provider**: Hetzner CPX41
- **Cost**: €35/month (~$39/month)
- **Capacity**: 10-15 bots
- **Total First Year**: ~$468/year

### Comparison to AWS
- **AWS Equivalent**: $100-500/month minimum
- **Savings with Hetzner**: $960-5,580/year

---

## 🔗 Useful Resources

### Provider Links
- Hetzner Cloud: https://www.hetzner.com/cloud
- DigitalOcean: https://www.digitalocean.com
- AWS: https://aws.amazon.com

### DEX Documentation
- Hyperliquid API: https://hyperliquid.gitbook.io/hyperliquid-docs/
- dYdX v4 Docs: https://docs.dydx.exchange/
- Vertex Protocol: https://vertexprotocol.com/
- Lighter Docs: https://docs.lighter.xyz

### Tools
- Grafana: https://grafana.com
- Prometheus: https://prometheus.io
- Uptime Kuma: https://github.com/louislam/uptime-kuma
- FastAPI: https://fastapi.tiangolo.com

---

**Recommendation**: Start with Hetzner CPX31 (€17/month) in Germany or USA, deploy current bots as systemd services, add Grafana for monitoring, and build simple FastAPI control endpoint. This gives you 24/7 operation, remote access, and easy scalability for under $20/month.
