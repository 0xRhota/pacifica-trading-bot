#!/usr/bin/env python3
"""
Automated Strategy Discovery Runner
Runs RBI backtest suite periodically and saves proven strategies

Usage:
    python3 rbi_agent/auto_discover_strategies.py --hours 2 --check-interval 30
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import argparse

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import RBI agent components
import importlib.util
rbi_agent_file = os.path.join(parent_dir, 'rbi_agent', 'rbi_agent.py')
spec = importlib.util.spec_from_file_location("rbi_agent", rbi_agent_file)
rbi_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rbi_module)
RBIAgent = rbi_module.RBIAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rbi_auto_discovery.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


STRATEGIES_TO_TEST = [
    # RSI-based
    {"name": "RSI Oversold Long", "description": "Buy when RSI < 30"},
    {"name": "RSI Oversold + Volume", "description": "Buy when RSI < 30 and volume increases 30%"},
    {"name": "RSI Overbought Short", "description": "Sell when RSI > 70"},
    {"name": "RSI Overbought + Volume", "description": "Sell when RSI > 70 and volume increases 30%"},
    
    # Moving averages
    {"name": "SMA Golden Cross", "description": "Buy when SMA(20) crosses above SMA(50) from below"},
    {"name": "SMA Death Cross", "description": "Sell when SMA(20) crosses below SMA(50) from above"},
    {"name": "Price Above SMA20", "description": "Buy when price is above SMA(20) and RSI < 50"},
    
    # Bollinger Bands
    {"name": "BB Lower Band Bounce", "description": "Buy when price touches Bollinger Band lower and RSI < 35"},
    {"name": "BB Upper Band Rejection", "description": "Sell when price touches Bollinger Band upper and RSI > 65"},
    
    # MACD
    {"name": "MACD Bullish Cross", "description": "Buy when MACD crosses above MACD signal line"},
    {"name": "MACD Bearish Cross", "description": "Sell when MACD crosses below MACD signal line"},
    
    # Combined
    {"name": "RSI + MACD Long", "description": "Buy when RSI < 40 and MACD crosses above signal"},
    {"name": "RSI + MACD Short", "description": "Sell when RSI > 60 and MACD crosses below signal"},
    {"name": "Multi-Indicator Long", "description": "Buy when RSI < 35 and price above SMA(20) and MACD is positive"},
    {"name": "Multi-Indicator Short", "description": "Sell when RSI > 65 and price below SMA(20) and MACD is negative"},
    
    # Volume-based
    {"name": "Volume Spike Long", "description": "Buy when volume increases 50% and RSI < 45"},
    {"name": "Volume Spike Short", "description": "Sell when volume increases 50% and RSI > 55"},
    
    # Conservative
    {"name": "Conservative RSI Long", "description": "Buy when RSI < 35 and price above SMA(50)"},
    {"name": "Conservative RSI Short", "description": "Sell when RSI > 65 and price below SMA(50)"},
]

PROVEN_STRATEGIES_FILE = "rbi_agent/proven_strategies.json"
DISCOVERY_LOG_FILE = "logs/rbi_discovery.log"


def load_proven_strategies() -> List[Dict]:
    """Load previously proven strategies"""
    if os.path.exists(PROVEN_STRATEGIES_FILE):
        try:
            with open(PROVEN_STRATEGIES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading proven strategies: {e}")
            return []
    return []


def save_proven_strategies(strategies: List[Dict]):
    """Save proven strategies to file"""
    try:
        # Sort by return (descending)
        strategies.sort(key=lambda x: x.get('return_pct', 0), reverse=True)
        
        with open(PROVEN_STRATEGIES_FILE, 'w') as f:
            json.dump(strategies, f, indent=2)
        
        logger.info(f"✅ Saved {len(strategies)} proven strategies to {PROVEN_STRATEGIES_FILE}")
    except Exception as e:
        logger.error(f"Error saving proven strategies: {e}")


def discover_strategies(
    days_back: int = 90,
    symbols: List[str] = None,
    min_return: float = 1.0,
    min_win_rate: float = 0.40,
    min_sharpe: float = 0.5
) -> List[Dict]:
    """
    Discover and test strategies
    
    Returns:
        List of proven strategies that passed thresholds
    """
    if symbols is None:
        symbols = ["SOL", "ETH", "BTC"]
    
    logger.info("=" * 80)
    logger.info("AUTOMATED STRATEGY DISCOVERY")
    logger.info("=" * 80)
    logger.info(f"Testing {len(STRATEGIES_TO_TEST)} strategies")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Period: Last {days_back} days")
    logger.info(f"Thresholds: Return > {min_return}%, Win Rate > {min_win_rate:.0%}, Sharpe > {min_sharpe}")
    logger.info("=" * 80)
    
    # Initialize RBI agent
    try:
        agent = RBIAgent()
    except Exception as e:
        logger.error(f"Failed to initialize RBI agent: {e}")
        return []
    
    proven_strategies = []
    
    for i, strategy in enumerate(STRATEGIES_TO_TEST, 1):
        logger.info(f"\n[{i}/{len(STRATEGIES_TO_TEST)}] Testing: {strategy['name']}")
        logger.info(f"Description: {strategy['description']}")
        
        try:
            result = agent.test_strategy(
                strategy_description=strategy['description'],
                symbols=symbols,
                days_back=days_back,
                min_return=min_return,
                min_win_rate=min_win_rate,
                min_sharpe=min_sharpe
            )
            
            if result.get('passed', False):
                strategy_data = {
                    'strategy_name': strategy['name'],
                    'description': result['strategy_description'],
                    'code': result['strategy_code'],
                    'return_pct': result['return_pct'],
                    'win_rate': result['win_rate'],
                    'sharpe_ratio': result['sharpe_ratio'],
                    'max_drawdown': result['max_drawdown'],
                    'total_trades': result['total_trades'],
                    'results_by_symbol': result.get('results_by_symbol', {}),
                    'discovered_at': datetime.now().isoformat()
                }
                
                proven_strategies.append(strategy_data)
                
                logger.info(f"  ✅ PROVEN: {result['return_pct']:.2f}% return, "
                           f"{result['win_rate']:.1%} win rate, "
                           f"{result['sharpe_ratio']:.2f} Sharpe")
            else:
                logger.info(f"  ❌ FAILED: {result.get('return_pct', 0):.2f}% return")
                
        except Exception as e:
            logger.error(f"  ❌ ERROR: {str(e)}")
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"DISCOVERY COMPLETE: {len(proven_strategies)} proven strategies found")
    logger.info(f"{'=' * 80}")
    
    return proven_strategies


def run_discovery_loop(
    hours: int = 2,
    check_interval_minutes: int = 30,
    days_back: int = 90
):
    """
    Run discovery loop for specified hours
    
    Args:
        hours: How many hours to run
        check_interval_minutes: Minutes between discovery runs
        days_back: Days of historical data for backtesting
    """
    end_time = datetime.now() + timedelta(hours=hours)
    check_interval_seconds = check_interval_minutes * 60
    
    logger.info("=" * 80)
    logger.info("AUTOMATED STRATEGY DISCOVERY LOOP")
    logger.info("=" * 80)
    logger.info(f"Running for {hours} hours")
    logger.info(f"Check interval: {check_interval_minutes} minutes")
    logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    # Load existing proven strategies
    all_proven = load_proven_strategies()
    logger.info(f"Loaded {len(all_proven)} existing proven strategies")
    
    run_count = 0
    
    while datetime.now() < end_time:
        run_count += 1
        logger.info(f"\n{'=' * 80}")
        logger.info(f"DISCOVERY RUN #{run_count}")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Time remaining: {end_time - datetime.now()}")
        logger.info(f"{'=' * 80}")
        
        # Discover strategies
        new_proven = discover_strategies(days_back=days_back)
        
        # Merge with existing (avoid duplicates)
        existing_names = {s['strategy_name'] for s in all_proven}
        for strategy in new_proven:
            if strategy['strategy_name'] not in existing_names:
                all_proven.append(strategy)
                logger.info(f"  ✅ New strategy discovered: {strategy['strategy_name']}")
            else:
                logger.info(f"  ⏭️  Strategy already known: {strategy['strategy_name']}")
        
        # Save updated list
        save_proven_strategies(all_proven)
        
        # Wait for next check
        if datetime.now() < end_time:
            wait_seconds = min(check_interval_seconds, (end_time - datetime.now()).total_seconds())
            logger.info(f"\n⏳ Waiting {wait_seconds/60:.1f} minutes until next discovery run...")
            time.sleep(wait_seconds)
    
    logger.info(f"\n{'=' * 80}")
    logger.info(f"DISCOVERY LOOP COMPLETE")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total runs: {run_count}")
    logger.info(f"Total proven strategies: {len(all_proven)}")
    logger.info(f"Results saved to: {PROVEN_STRATEGIES_FILE}")
    logger.info(f"{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(description="Automated Strategy Discovery")
    parser.add_argument("--hours", type=int, default=2, help="Hours to run discovery loop (default: 2)")
    parser.add_argument("--check-interval", type=int, default=30, help="Minutes between runs (default: 30)")
    parser.add_argument("--days", type=int, default=90, help="Days of historical data (default: 90)")
    parser.add_argument("--once", action="store_true", help="Run once and exit (don't loop)")
    parser.add_argument("--symbols", type=str, nargs="+", default=["SOL", "ETH", "BTC"], help="Symbols to test")
    
    args = parser.parse_args()
    
    if args.once:
        # Single run
        proven = discover_strategies(days_back=args.days, symbols=args.symbols)
        all_proven = load_proven_strategies()
        
        # Merge
        existing_names = {s['strategy_name'] for s in all_proven}
        for strategy in proven:
            if strategy['strategy_name'] not in existing_names:
                all_proven.append(strategy)
        
        save_proven_strategies(all_proven)
        
        print(f"\n✅ Discovery complete: {len(proven)} new strategies found")
        print(f"📄 Total proven strategies: {len(all_proven)}")
        print(f"📄 Saved to: {PROVEN_STRATEGIES_FILE}")
    else:
        # Continuous loop
        run_discovery_loop(
            hours=args.hours,
            check_interval_minutes=args.check_interval,
            days_back=args.days
        )


if __name__ == "__main__":
    main()

