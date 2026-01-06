# Smart Money Data: API Comparison

## Lighter vs Hyperliquid

| Data Type | Lighter | Hyperliquid |
|-----------|---------|-------------|
| Recent Trades | `/recentTrades` | `/info` (userFills) |
| Order Book | `/orderbookorders` | `/info` (l2Book) |
| Positions | `/accounts/{}/positions` | `/info` (clearinghouseState) |
| Liquidations | `/liquidations` | `/info` (userFunding) |
| Funding Rates | `/funding-rates` | `/info` (fundingHistory) |
| **User Identification** | Account Index | Wallet Address |

## Key Difference: Identity

- **Lighter**: Uses account indices, not wallet addresses publicly
- **Hyperliquid**: Uses EVM wallet addresses (0x...) - fully transparent

**Hyperliquid advantage**: Can track same wallet across trades, see full history by address.

## Cross-Exchange Tracking: Is It Possible?

**Short answer: Mostly NO**

| Exchange | Chain | Identity |
|----------|-------|----------|
| Lighter | ZK rollup | Account index (opaque) |
| Hyperliquid | L1 (own chain) | EVM address |
| Hibachi | ?? | Account ID |

**Problem**: Different identity systems. No shared wallet addresses.

**Possible workarounds**:
1. **Deposit/Withdraw tracking** - If user bridges from same L1 wallet, could correlate
2. **Behavioral fingerprinting** - Trading patterns, timing, size preferences
3. **Cross-reference funding wallets** - On-chain deposit sources

## What Coinglass Does (Hyperliquid)

[Coinglass Whale Tracking](https://docs.coinglass.com/reference/hyperliquid-whale-position):
- Positions > $1M notional
- Real-time alerts
- ~200 most recent whale moves

**They don't offer this for Lighter** (yet).

## Lighter Trade Fields (from SDK)

```
trade_id, tx_hash, market_id, timestamp
price, size, usd_amount
ask_account_id, bid_account_id        <-- Account IDs (not wallets)
is_maker_ask
taker_position_size_before            <-- Can see position size!
maker_position_size_before
taker_fee, maker_fee
```

**Key insight**: We get `account_id` not wallet addresses. But we CAN see:
- Position sizes before trade (whale detection)
- USD amounts per trade (filter for large trades)
- Maker vs taker (informed vs liquidity taker)

---

## CREATIVE FINDS (Deeper API Dig)

### 1. **L1 Address IS Available**
`DetailedAccount.l1_address` = actual wallet address!
- Can link account_id → wallet → on-chain history
- Cross-reference with Solana/ETH activity

### 2. **Order Book Shows WHO**
`Order.owner_account_index` on every order
- See which accounts have large limit orders sitting
- "Whale walls" with attribution

### 3. **Liquidation Intelligence**
`AccountPosition.liquidation_price` per account
- Find accounts close to liquidation
- Predict cascade events
- Front-run liquidation squeezes

### 4. **P/L Leaderboard Possible**
`AccountPosition.realized_pnl` + `unrealized_pnl`
- Build smart money leaderboard
- Track who's actually profitable
- Copy their trades

### 5. **Funding Drain Detection**
`AccountPosition.total_funding_paid_out`
- Find overleveraged longs/shorts bleeding funding
- They may capitulate soon

### 6. **Volume Leaders**
`AccountTradeStats.total_volume` per account
- Identify most active traders
- Correlate volume with profitability

---

## Actionable Ideas

| Idea | Data Source | Edge |
|------|-------------|------|
| Copy profitable traders | realized_pnl leaderboard | Follow winners |
| Liquidation cascade alerts | accounts near liq_price | Front-run squeezes |
| Whale wall detection | orderbook + owner_account | See large limits |
| Wallet cross-reference | l1_address | Link to on-chain |
| Funding bleed alerts | total_funding_paid_out | Predict capitulation |

## Next Steps

1. [x] ~~Check if account_id can be linked to wallet~~ YES via l1_address
2. [ ] Build: Pull top 20 accounts by realized_pnl
3. [ ] Build: Scan orderbook for whale limit orders
4. [ ] Build: Find accounts within 5% of liquidation
