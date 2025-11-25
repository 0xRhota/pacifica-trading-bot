"""
Risk management system for Pacifica trading bot
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    total_volume: float = 0.0
    total_trades: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profitable_trades: int = 0
    losing_trades: int = 0
    last_reset: float = field(default_factory=time.time)

@dataclass
class PositionRisk:
    symbol: str
    size: float
    value_usd: float
    max_loss_usd: float
    time_held: float
    risk_level: str  # "low", "medium", "high"

class RiskManager:
    """Comprehensive risk management system"""
    
    def __init__(self, config):
        self.config = config
        self.metrics = RiskMetrics()
        self.daily_trades: List[Dict] = []
        self.position_history: List[Dict] = []
        self.emergency_stop = False
        
    def check_can_trade(self, symbol: str, position_size_usd: float) -> Tuple[bool, str]:
        """Check if we can safely place a trade"""
        
        # Emergency stop check
        if self.emergency_stop:
            return False, "Emergency stop activated"
            
        # Daily loss limit check
        if hasattr(self.config, 'MAX_DAILY_LOSS'):
            if self.metrics.daily_pnl <= -self.config.MAX_DAILY_LOSS:
                return False, f"Daily loss limit reached: ${abs(self.metrics.daily_pnl):.2f}"
        
        # Position size check
        if hasattr(self.config, 'MAX_POSITION_SIZE_USD'):
            if position_size_usd > self.config.MAX_POSITION_SIZE_USD:
                return False, f"Position size too large: ${position_size_usd:.2f} > ${self.config.MAX_POSITION_SIZE_USD:.2f}"
        
        # Check if we're trading too frequently
        recent_trades = [t for t in self.daily_trades if time.time() - t.get('timestamp', 0) < 300]  # 5 minutes
        if len(recent_trades) > 20:  # Max 20 trades per 5 minutes
            return False, "Trading frequency limit reached"
            
        # All checks passed
        return True, "OK"
    
    def calculate_position_size(self, symbol: str, account_balance: float, signal_confidence: float) -> float:
        """Calculate safe position size based on risk parameters"""
        
        # Base position size from config
        base_size = getattr(self.config, 'SMALL_TRADE_SIZE', 50.0)
        
        # Adjust based on confidence
        confidence_multiplier = min(signal_confidence, 1.0)
        
        # Adjust based on recent performance
        if self.metrics.win_rate > 0.6:
            performance_multiplier = 1.2  # Increase size if performing well
        elif self.metrics.win_rate < 0.4:
            performance_multiplier = 0.8  # Decrease size if performing poorly
        else:
            performance_multiplier = 1.0
            
        # Adjust based on account balance (never risk more than 5% of balance per trade)
        max_risk_per_trade = account_balance * 0.05
        
        calculated_size = base_size * confidence_multiplier * performance_multiplier
        final_size = min(calculated_size, max_risk_per_trade)
        
        logger.info(f"Position size calculation: base=${base_size}, confidence={confidence_multiplier:.2f}, performance={performance_multiplier:.2f}, final=${final_size:.2f}")
        
        return final_size
    
    def record_trade_opened(self, symbol: str, side: str, size: float, price: float):
        """Record when a trade is opened"""
        trade = {
            'symbol': symbol,
            'side': side,
            'size': size,
            'entry_price': price,
            'timestamp': time.time(),
            'status': 'open'
        }
        
        self.daily_trades.append(trade)
        self.metrics.total_trades += 1
        self.metrics.total_volume += abs(size) * price
        
        logger.info(f"Trade opened: {symbol} {side} {size:.6f} @ ${price:.4f}")
    
    def record_trade_closed(self, symbol: str, exit_price: float, pnl: float):
        """Record when a trade is closed"""
        
        # Find the corresponding open trade
        for trade in reversed(self.daily_trades):
            if trade['symbol'] == symbol and trade['status'] == 'open':
                trade['exit_price'] = exit_price
                trade['pnl'] = pnl
                trade['status'] = 'closed'
                trade['duration'] = time.time() - trade['timestamp']
                break
        
        # Update metrics
        self.metrics.total_pnl += pnl
        self.metrics.daily_pnl += pnl
        
        if pnl > 0:
            self.metrics.profitable_trades += 1
        else:
            self.metrics.losing_trades += 1
            
        # Update win rate
        total_closed_trades = self.metrics.profitable_trades + self.metrics.losing_trades
        if total_closed_trades > 0:
            self.metrics.win_rate = self.metrics.profitable_trades / total_closed_trades
        
        # Check for max drawdown
        if self.metrics.daily_pnl < self.metrics.max_drawdown:
            self.metrics.max_drawdown = self.metrics.daily_pnl
            
        # Emergency stop if losses are too high
        if hasattr(self.config, 'MAX_DAILY_LOSS'):
            if self.metrics.daily_pnl <= -self.config.MAX_DAILY_LOSS:
                self.emergency_stop = True
                logger.error(f"EMERGENCY STOP: Daily loss limit reached: ${abs(self.metrics.daily_pnl):.2f}")
        
        logger.info(f"Trade closed: {symbol} P&L=${pnl:.2f}, Daily P&L=${self.metrics.daily_pnl:.2f}, Win rate={self.metrics.win_rate:.2f}")
    
    def assess_position_risk(self, symbol: str, size: float, entry_price: float, current_price: float, hold_time: float) -> PositionRisk:
        """Assess risk level of current position"""
        
        value_usd = abs(size) * current_price
        
        # Calculate unrealized P&L
        if size > 0:  # Long position
            unrealized_pnl = (current_price - entry_price) * size
        else:  # Short position
            unrealized_pnl = (entry_price - current_price) * abs(size)
            
        unrealized_pnl_pct = unrealized_pnl / (abs(size) * entry_price)
        
        # Determine risk level
        if abs(unrealized_pnl_pct) > 0.02:  # 2% loss
            risk_level = "high"
        elif abs(unrealized_pnl_pct) > 0.01:  # 1% loss
            risk_level = "medium"
        else:
            risk_level = "low"
            
        # Time-based risk (positions held too long are riskier)
        if hold_time > getattr(self.config, 'MAX_POSITION_HOLD_TIME', 120):
            risk_level = "high"
        
        return PositionRisk(
            symbol=symbol,
            size=size,
            value_usd=value_usd,
            max_loss_usd=abs(unrealized_pnl) if unrealized_pnl < 0 else 0,
            time_held=hold_time,
            risk_level=risk_level
        )
    
    def should_close_position(self, position_risk: PositionRisk, unrealized_pnl_pct: float) -> Tuple[bool, str]:
        """Determine if position should be closed"""
        
        # Profit taking
        min_profit = getattr(self.config, 'MIN_PROFIT_THRESHOLD', 0.001)
        if unrealized_pnl_pct >= min_profit:
            return True, f"Take profit: {unrealized_pnl_pct:.4f}%"
        
        # Stop loss
        max_loss = getattr(self.config, 'MAX_LOSS_THRESHOLD', 0.002)
        if unrealized_pnl_pct <= -max_loss:
            return True, f"Stop loss: {unrealized_pnl_pct:.4f}%"
        
        # Time-based exit
        max_hold_time = getattr(self.config, 'MAX_POSITION_HOLD_TIME', 120)
        if position_risk.time_held > max_hold_time:
            return True, f"Time exit: held for {position_risk.time_held:.1f}s"
        
        # High risk positions
        if position_risk.risk_level == "high":
            return True, f"High risk position"
        
        return False, "Hold position"
    
    def get_risk_summary(self) -> Dict:
        """Get current risk summary"""
        return {
            'total_volume': self.metrics.total_volume,
            'total_trades': self.metrics.total_trades,
            'daily_pnl': self.metrics.daily_pnl,
            'total_pnl': self.metrics.total_pnl,
            'win_rate': self.metrics.win_rate,
            'max_drawdown': self.metrics.max_drawdown,
            'emergency_stop': self.emergency_stop,
            'recent_trades': len([t for t in self.daily_trades if time.time() - t.get('timestamp', 0) < 3600])  # Last hour
        }
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of each day)"""
        logger.info("Resetting daily metrics")
        self.metrics.daily_pnl = 0.0
        self.metrics.max_drawdown = 0.0
        self.metrics.last_reset = time.time()
        self.daily_trades = []
        self.emergency_stop = False