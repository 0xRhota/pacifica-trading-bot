#!/usr/bin/env python3
"""
Pacifica Volume Farming Bot - Main Entry Point
Optimized for maximum volume generation with minimal risk
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
import json

from pacifica_bot import VolumeBot, TradingConfig, Position
from risk_manager import RiskManager
from config import BotConfig

# Setup logging
logging.basicConfig(
    level=getattr(logging, BotConfig.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BotConfig.LOG_FILE) if BotConfig.LOG_TO_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

class EnhancedVolumeBot(VolumeBot):
    """Enhanced volume bot with risk management"""
    
    def __init__(self, config: TradingConfig):
        super().__init__(config)
        self.risk_manager = RiskManager(BotConfig)
        
    async def _execute_volume_strategy(self, symbol: str):
        """Enhanced volume strategy with risk management"""
        try:
            # Get current market data
            price = await self.api.get_market_price(symbol)
            if not price:
                return
            
            # Check if we have an existing position
            if symbol in self.positions:
                await self._manage_existing_position_with_risk(symbol, price)
            else:
                await self._open_new_position_with_risk(symbol, price)
                
        except Exception as e:
            logger.error(f"Error in enhanced volume strategy for {symbol}: {e}")
    
    async def _open_new_position_with_risk(self, symbol: str, current_price: float):
        """Open new position with risk management"""
        
        # Get account info for balance
        account = await self.api.get_account_info()
        balance = float(account.get('equity', 1000.0)) if account else 1000.0
        
        # Calculate position size using risk management
        signal_confidence = 0.7  # Default confidence for volume farming
        position_value = self.risk_manager.calculate_position_size(symbol, balance, signal_confidence)
        
        # Check if we can trade
        can_trade, reason = self.risk_manager.check_can_trade(symbol, position_value)
        if not can_trade:
            logger.warning(f"Cannot trade {symbol}: {reason}")
            return
        
        # Calculate size
        size = position_value / current_price
        
        # Determine side (alternate for volume farming)
        side = "buy" if self.trades_count % 2 == 0 else "sell"
        
        logger.info(f"Opening {side} position for {symbol}: ${position_value:.2f} ({size:.6f} units) @ ${current_price:.4f}")
        
        # Place order
        order = await self.api.create_market_order(symbol, side, size)
        
        if order and "id" in order:
            # Record with risk manager
            self.risk_manager.record_trade_opened(symbol, side, size, current_price)
            
            # Record position
            self.positions[symbol] = Position(
                symbol=symbol,
                size=size if side == "buy" else -size,
                entry_price=current_price,
                side=side,
                timestamp=time.time()
            )
            
            self.trades_count += 1
            self.total_volume += position_value
            
            logger.info(f"Position opened successfully. Total volume: ${self.total_volume:.2f}")
    
    async def _manage_existing_position_with_risk(self, symbol: str, current_price: float):
        """Manage existing position with enhanced risk management"""
        position = self.positions[symbol]
        
        # Calculate current P&L
        if position.side == "buy":
            unrealized_pnl = (current_price - position.entry_price) * position.size
            pnl_pct = (current_price - position.entry_price) / position.entry_price
        else:
            unrealized_pnl = (position.entry_price - current_price) * abs(position.size)
            pnl_pct = (position.entry_price - current_price) / position.entry_price
        
        # Get risk assessment
        hold_time = time.time() - position.timestamp
        position_risk = self.risk_manager.assess_position_risk(
            symbol, position.size, position.entry_price, current_price, hold_time
        )
        
        # Check if we should close
        should_close, close_reason = self.risk_manager.should_close_position(position_risk, pnl_pct)
        
        if should_close:
            await self._close_position_with_risk(symbol, current_price, unrealized_pnl)
            logger.info(f"Position closed: {close_reason}, P&L: ${unrealized_pnl:.2f} ({pnl_pct:.4f}%)")
    
    async def _close_position_with_risk(self, symbol: str, current_price: float, pnl: float):
        """Close position and update risk metrics"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        close_side = "sell" if position.side == "buy" else "buy"
        
        # Place closing order
        order = await self.api.create_market_order(symbol, close_side, abs(position.size))
        
        if order:
            # Update risk manager
            self.risk_manager.record_trade_closed(symbol, current_price, pnl)
            
            # Update volume
            position_value = abs(position.size) * current_price
            self.total_volume += position_value
            self.trades_count += 1
            
            # Remove position
            del self.positions[symbol]
            
            logger.info(f"Position closed for {symbol}. Total volume: ${self.total_volume:.2f}")
    
    async def print_status(self):
        """Print current bot status"""
        risk_summary = self.risk_manager.get_risk_summary()
        
        print("\n" + "="*60)
        print(f"PACIFICA VOLUME BOT STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print(f"Total Volume:      ${risk_summary['total_volume']:,.2f}")
        print(f"Total Trades:      {risk_summary['total_trades']}")
        print(f"Daily P&L:         ${risk_summary['daily_pnl']:,.2f}")
        print(f"Total P&L:         ${risk_summary['total_pnl']:,.2f}")
        print(f"Win Rate:          {risk_summary['win_rate']:.1%}")
        print(f"Max Drawdown:      ${risk_summary['max_drawdown']:,.2f}")
        print(f"Active Positions:  {len(self.positions)}")
        print(f"Emergency Stop:    {'YES' if risk_summary['emergency_stop'] else 'NO'}")
        print("="*60)
        
        if self.positions:
            print("ACTIVE POSITIONS:")
            for symbol, pos in self.positions.items():
                print(f"  {symbol}: {pos.side} {abs(pos.size):.6f} @ ${pos.entry_price:.4f}")
        print()

async def main():
    """Main bot execution"""
    print("🚀 Starting Pacifica Volume Farming Bot...")
    print(f"Target: Maximize volume on {', '.join(BotConfig.TRADING_SYMBOLS)}")
    print(f"Max position size: ${BotConfig.MAX_POSITION_SIZE_USD}")
    print(f"Trade frequency: {BotConfig.TRADE_FREQUENCY_SECONDS}s")
    print()
    
    # Create configuration
    config = TradingConfig(
        api_key=BotConfig.API_KEY,
        base_url=BotConfig.BASE_URL,
        max_position_size=BotConfig.MAX_POSITION_SIZE_USD,
        min_profit_threshold=BotConfig.MIN_PROFIT_THRESHOLD,
        max_loss_threshold=BotConfig.MAX_LOSS_THRESHOLD,
        trade_frequency=BotConfig.TRADE_FREQUENCY_SECONDS,
        symbols=BotConfig.TRADING_SYMBOLS
    )
    
    # Create enhanced bot
    bot = EnhancedVolumeBot(config)
    
    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start status reporting task
    async def status_reporter():
        while bot.running:
            await bot.print_status()
            await asyncio.sleep(60)  # Print status every minute
    
    try:
        # Start bot and status reporter
        await asyncio.gather(
            bot.start(),
            status_reporter()
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.stop()
        
        # Final summary
        risk_summary = bot.risk_manager.get_risk_summary()
        print("\n🏁 FINAL SUMMARY:")
        print(f"Total Volume Generated: ${risk_summary['total_volume']:,.2f}")
        print(f"Total Trades: {risk_summary['total_trades']}")
        print(f"Final P&L: ${risk_summary['total_pnl']:,.2f}")
        print(f"Win Rate: {risk_summary['win_rate']:.1%}")

if __name__ == "__main__":
    asyncio.run(main())