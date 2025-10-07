# Pacifica Volume Farming Bot

A sophisticated trading bot designed to maximize trading volume on Pacifica.fi while minimizing risk. Built for the Pacifica points program that rewards users based on trading activity.

## Features

- **Volume Maximization**: Optimized to generate maximum trading volume through rapid open/close cycles
- **Risk Management**: Comprehensive risk controls to protect capital
- **Multiple Strategies**: Volume farming, spread capture, and momentum trading
- **Real-time Monitoring**: Live status updates and performance metrics
- **Emergency Controls**: Automatic stop-loss and daily loss limits

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key**:
   Edit `config.py` and add your Pacifica API key:
   ```python
   API_KEY = "your_api_key_here"
   ```

3. **Run the Bot**:
   ```bash
   python main.py
   ```

## Configuration

Key settings in `config.py`:

- `MAX_POSITION_SIZE_USD`: Maximum position size (default: $100)
- `TRADE_FREQUENCY_SECONDS`: Time between trades (default: 30s)
- `MIN_PROFIT_THRESHOLD`: Minimum profit to close position (default: 0.05%)
- `MAX_LOSS_THRESHOLD`: Maximum loss before stop-loss (default: 0.1%)
- `TRADING_SYMBOLS`: Symbols to trade (SOL-USD, BTC-USD, ETH-USD)

## Strategies

### 1. Volume Farming Strategy
- Opens small positions alternating between long/short
- Closes positions quickly for small profits or acceptable losses
- Prioritizes volume generation over profit maximization

### 2. Spread Capture Strategy
- Monitors bid-ask spreads for opportunities
- Places orders between bid/ask to capture spread
- Low-risk, consistent small profits

### 3. Momentum Strategy
- Uses simple moving averages to detect momentum
- Follows short-term price movements
- Quick entries and exits

## Risk Management

- **Position Sizing**: Dynamic sizing based on account balance and confidence
- **Stop Losses**: Automatic position closure on excessive losses
- **Time Limits**: Maximum position hold time (2 minutes default)
- **Daily Limits**: Maximum daily loss protection
- **Emergency Stop**: Automatic shutdown on risk threshold breach

## Monitoring

The bot provides real-time status updates including:
- Total volume generated
- Number of trades executed
- Daily and total P&L
- Win rate and drawdown metrics
- Active positions

## API Integration

Built for Pacifica.fi REST API:
- Mainnet: `https://api.pacifica.fi/api/v1`
- Testnet: `https://test-api.pacifica.fi/api/v1`

Supports:
- Market orders
- Position monitoring
- Account information
- Real-time price data

## Safety Features

- **No Self-Trading**: Designed to avoid patterns flagged as manipulation
- **Organic Activity**: Mimics natural trading behavior
- **Rate Limiting**: Respects API rate limits
- **Error Handling**: Robust error recovery

## Volume Optimization

The bot is specifically optimized for Pacifica's points program:
- Maximizes legitimate trading volume
- Avoids patterns that don't earn points
- Balances volume generation with profitability
- Designed for sustained operation

## Legal Disclaimer

This bot is for educational purposes. Trading involves risk of loss. Users are responsible for compliance with platform terms of service and applicable regulations.

## Support

For issues or questions, check the logs in `trading_bot.log` for detailed operation information.