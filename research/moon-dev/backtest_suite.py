#!/usr/bin/env python3
"""
RBI Strategy Backtesting Suite
Tests multiple strategies on 90 days of historical Pacifica data
Finds the best performing strategies based on return, win rate, and Sharpe ratio

Usage:
    python rbi_agent/backtest_suite.py
"""

import os
import sys
import json
import logging
from typing import List, Dict
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Import RBI agent (direct import)
import importlib.util
rbi_agent_file = os.path.join(parent_dir, 'rbi_agent', 'rbi_agent.py')
spec = importlib.util.spec_from_file_location("rbi_agent", rbi_agent_file)
rbi_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rbi_module)
RBIAgent = rbi_module.RBIAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Strategy library - common trading strategies to test
STRATEGIES = [
    # RSI-based strategies
    {
        "name": "RSI Oversold Long",
        "description": "Buy when RSI < 30",
        "category": "momentum"
    },
    {
        "name": "RSI Oversold + Volume",
        "description": "Buy when RSI < 30 and volume increases 30%",
        "category": "momentum"
    },
    {
        "name": "RSI Overbought Short",
        "description": "Sell when RSI > 70",
        "category": "mean_reversion"
    },
    {
        "name": "RSI Overbought + Volume",
        "description": "Sell when RSI > 70 and volume increases 30%",
        "category": "mean_reversion"
    },
    
    # Moving average strategies
    {
        "name": "SMA Golden Cross",
        "description": "Buy when SMA(20) crosses above SMA(50) from below",
        "category": "trend_following"
    },
    {
        "name": "SMA Death Cross",
        "description": "Sell when SMA(20) crosses below SMA(50) from above",
        "category": "trend_following"
    },
    {
        "name": "Price Above SMA20",
        "description": "Buy when price is above SMA(20) and RSI < 50",
        "category": "trend_following"
    },
    
    # Bollinger Bands strategies
    {
        "name": "BB Lower Band Bounce",
        "description": "Buy when price touches Bollinger Band lower and RSI < 35",
        "category": "mean_reversion"
    },
    {
        "name": "BB Upper Band Rejection",
        "description": "Sell when price touches Bollinger Band upper and RSI > 65",
        "category": "mean_reversion"
    },
    
    # MACD strategies
    {
        "name": "MACD Bullish Cross",
        "description": "Buy when MACD crosses above MACD signal line",
        "category": "momentum"
    },
    {
        "name": "MACD Bearish Cross",
        "description": "Sell when MACD crosses below MACD signal line",
        "category": "momentum"
    },
    
    # Combined strategies
    {
        "name": "RSI + MACD Long",
        "description": "Buy when RSI < 40 and MACD crosses above signal",
        "category": "momentum"
    },
    {
        "name": "RSI + MACD Short",
        "description": "Sell when RSI > 60 and MACD crosses below signal",
        "category": "momentum"
    },
    {
        "name": "Multi-Indicator Long",
        "description": "Buy when RSI < 35 and price above SMA(20) and MACD is positive",
        "category": "momentum"
    },
    {
        "name": "Multi-Indicator Short",
        "description": "Sell when RSI > 65 and price below SMA(20) and MACD is negative",
        "category": "momentum"
    },
    
    # Volume-based strategies
    {
        "name": "Volume Spike Long",
        "description": "Buy when volume increases 50% and RSI < 45",
        "category": "momentum"
    },
    {
        "name": "Volume Spike Short",
        "description": "Sell when volume increases 50% and RSI > 55",
        "category": "momentum"
    },
    
    # Conservative strategies
    {
        "name": "Conservative RSI Long",
        "description": "Buy when RSI < 35 and price above SMA(50)",
        "category": "trend_following"
    },
    {
        "name": "Conservative RSI Short",
        "description": "Sell when RSI > 65 and price below SMA(50)",
        "category": "trend_following"
    },
]


def run_backtest_suite(
    days_back: int = 90,
    symbols: List[str] = None,
    min_return: float = 0.5,
    min_win_rate: float = 0.35,
    min_sharpe: float = 0.3
) -> Dict:
    """
    Run backtest suite on all strategies
    
    Args:
        days_back: Days of historical data to use
        symbols: List of symbols to test (default: SOL, ETH, BTC, PUMP)
        min_return: Minimum return % to consider (default: 0.5%)
        min_win_rate: Minimum win rate to consider (default: 35%)
        min_sharpe: Minimum Sharpe ratio to consider (default: 0.3)
        
    Returns:
        Dict with:
            - results: List of all strategy results
            - best_strategies: Top strategies by return
            - summary: Summary statistics
    """
    if symbols is None:
        symbols = ["SOL", "ETH", "BTC", "PUMP"]
    
    logger.info("=" * 80)
    logger.info("RBI BACKTEST SUITE")
    logger.info("=" * 80)
    logger.info(f"Testing {len(STRATEGIES)} strategies")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Period: Last {days_back} days")
    logger.info(f"Thresholds: Return > {min_return}%, Win Rate > {min_win_rate:.0%}, Sharpe > {min_sharpe}")
    logger.info("=" * 80)
    
    # Initialize RBI agent
    try:
        agent = RBIAgent()
    except Exception as e:
        logger.error(f"Failed to initialize RBI agent: {e}")
        return {"error": str(e)}
    
    # Test all strategies
    all_results = []
    
    for i, strategy in enumerate(STRATEGIES, 1):
        logger.info(f"\n[{i}/{len(STRATEGIES)}] Testing: {strategy['name']}")
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
            
            # Add strategy metadata
            result['strategy_name'] = strategy['name']
            result['category'] = strategy['category']
            
            all_results.append(result)
            
            status = "✅ PASSED" if result['passed'] else "❌ FAILED"
            logger.info(f"  {status} | Return: {result['return_pct']:.2f}% | "
                       f"Win Rate: {result['win_rate']:.1%} | "
                       f"Sharpe: {result['sharpe_ratio']:.2f} | "
                       f"Trades: {result['total_trades']}")
            
        except Exception as e:
            logger.error(f"  ❌ ERROR: {str(e)}")
            all_results.append({
                'strategy_name': strategy['name'],
                'category': strategy['category'],
                'passed': False,
                'error': str(e)
            })
    
    # Sort by return (descending)
    passed_results = [r for r in all_results if r.get('passed', False)]
    failed_results = [r for r in all_results if not r.get('passed', False)]
    
    passed_results.sort(key=lambda x: x.get('return_pct', 0), reverse=True)
    
    # Calculate summary statistics
    if passed_results:
        avg_return = sum(r['return_pct'] for r in passed_results) / len(passed_results)
        avg_win_rate = sum(r['win_rate'] for r in passed_results) / len(passed_results)
        avg_sharpe = sum(r['sharpe_ratio'] for r in passed_results) / len(passed_results)
        total_trades = sum(r['total_trades'] for r in passed_results)
    else:
        avg_return = 0.0
        avg_win_rate = 0.0
        avg_sharpe = 0.0
        total_trades = 0
    
    summary = {
        'total_strategies': len(STRATEGIES),
        'passed': len(passed_results),
        'failed': len(failed_results),
        'avg_return': avg_return,
        'avg_win_rate': avg_win_rate,
        'avg_sharpe': avg_sharpe,
        'total_trades': total_trades
    }
    
    # Get top 10 strategies
    top_strategies = passed_results[:10]
    
    return {
        'results': all_results,
        'best_strategies': top_strategies,
        'summary': summary,
        'timestamp': datetime.now().isoformat(),
        'config': {
            'days_back': days_back,
            'symbols': symbols,
            'min_return': min_return,
            'min_win_rate': min_win_rate,
            'min_sharpe': min_sharpe
        }
    }


def print_results(results: Dict):
    """Print formatted results"""
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 80)
    
    summary = results['summary']
    print(f"\nTotal Strategies Tested: {summary['total_strategies']}")
    print(f"Passed: {summary['passed']} | Failed: {summary['failed']}")
    
    if summary['passed'] > 0:
        print(f"\nAverage Performance (Passed Strategies):")
        print(f"  Return: {summary['avg_return']:.2f}%")
        print(f"  Win Rate: {summary['avg_win_rate']:.1%}")
        print(f"  Sharpe Ratio: {summary['avg_sharpe']:.2f}")
        print(f"  Total Trades: {summary['total_trades']}")
    
    if results['best_strategies']:
        print("\n" + "=" * 80)
        print("TOP 10 STRATEGIES (by Return)")
        print("=" * 80)
        
        for i, strategy in enumerate(results['best_strategies'], 1):
            print(f"\n{i}. {strategy['strategy_name']}")
            print(f"   Category: {strategy['category']}")
            print(f"   Description: {strategy['strategy_description']}")
            print(f"   ✅ Return: {strategy['return_pct']:.2f}%")
            print(f"   Win Rate: {strategy['win_rate']:.1%}")
            print(f"   Sharpe Ratio: {strategy['sharpe_ratio']:.2f}")
            print(f"   Max Drawdown: {strategy['max_drawdown']:.2f}%")
            print(f"   Total Trades: {strategy['total_trades']}")
            
            # Show results by symbol
            if 'results_by_symbol' in strategy:
                print(f"   Results by Symbol:")
                for symbol, symbol_result in strategy['results_by_symbol'].items():
                    print(f"     {symbol}: {symbol_result['return_pct']:.2f}% return, "
                          f"{symbol_result['win_rate']:.1%} win rate, "
                          f"{symbol_result['total_trades']} trades")
    else:
        print("\n❌ No strategies passed the thresholds")
        print("Try lowering thresholds or testing different strategies")
    
    print("\n" + "=" * 80)


def save_results(results: Dict, filename: str = "rbi_agent/backtest_results.json"):
    """Save results to JSON file"""
    try:
        # Convert datetime to string for JSON serialization
        results_copy = json.loads(json.dumps(results, default=str))
        
        with open(filename, 'w') as f:
            json.dump(results_copy, f, indent=2)
        
        logger.info(f"\n✅ Results saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RBI Strategy Backtesting Suite")
    parser.add_argument("--days", type=int, default=90, help="Days of historical data (default: 90)")
    parser.add_argument("--symbols", type=str, nargs="+", default=["SOL", "ETH", "BTC", "PUMP"], 
                       help="Symbols to test (default: SOL ETH BTC PUMP)")
    parser.add_argument("--min-return", type=float, default=0.5, help="Minimum return % to pass (default: 0.5)")
    parser.add_argument("--min-win-rate", type=float, default=0.35, help="Minimum win rate to pass (default: 0.35)")
    parser.add_argument("--min-sharpe", type=float, default=0.3, help="Minimum Sharpe ratio to pass (default: 0.3)")
    parser.add_argument("--no-save", action="store_true", help="Don't save results to file")
    
    args = parser.parse_args()
    
    # Run backtest suite
    results = run_backtest_suite(
        days_back=args.days,
        symbols=args.symbols,
        min_return=args.min_return,
        min_win_rate=args.min_win_rate,
        min_sharpe=args.min_sharpe
    )
    
    if 'error' in results:
        logger.error(f"Backtest suite failed: {results['error']}")
        return 1
    
    # Print results
    print_results(results)
    
    # Save results
    if not args.no_save:
        save_results(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

