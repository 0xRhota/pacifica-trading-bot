# Hibachi API Reference

**Official API Documentation**: https://api-doc.hibachi.xyz/
**Official Python SDK**: https://github.com/hibachi-xyz/hibachi_sdk (PyPI: `pip install hibachi-xyz`)

## Base URLs

- **Trading API**: `https://api.hibachi.xyz`
- **Data API**: `https://data-api.hibachi.xyz`

## Authentication

**Email/OAuth Accounts** (YOUR SETUP):
- Use `Authorization` header with API Key
- No complex signing for READ operations
- HMAC signing ONLY for WRITE operations (place/cancel orders)

```bash
Authorization: <YOUR_API_KEY>
```

## Key Endpoints

### Account API (requires auth)
```
GET  /capital/balance?accountId=<id>
GET  /trade/account/info?accountId=<id>
GET  /trade/orders?accountId=<id>
POST /trade/order
DELETE /trade/order
```

### Market Data API (public, no auth)
```
GET /market/exchange-info              # List all markets
GET /market/data/prices?symbol=BTC/USDT-P
GET /market/data/orderbook?symbol=BTC/USDT-P
GET /market/data/trades?symbol=BTC/USDT-P
```

## Markets Available
- BTC/USDT-P
- ETH/USDT-P
- SOL/USDT-P

## Notes
- Account ID required for all account/trade endpoints
- **Get Account ID from Hibachi UI**: Settings → API Keys → View API Key Details
- Add to .env as `HIBACHI_ACCOUNT_ID`
- Exchange-managed accounts use HMAC signing for orders
- Public key = API Key
- Private key = API Secret (HMAC shared secret)
- READ operations (GET): Simple `Authorization` header only
- WRITE operations (POST/DELETE orders): Require HMAC signature with timestamp
