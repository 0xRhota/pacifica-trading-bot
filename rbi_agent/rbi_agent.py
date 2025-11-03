"""
RBI (Research-Based Inference) Agent MVP
Automated strategy discovery and backtesting system

Based on Moon Dev's RBI agent concept:
- Takes trading strategy descriptions (natural language)
- Generates backtest code using LLM
- Tests strategies on historical Pacifica data
- Returns pass/fail with performance metrics

Usage:
    from rbi_agent import RBIAgent
    
    agent = RBIAgent(deepseek_api_key="your_key")
    
    # Test a strategy
    result = agent.test_strategy(
        strategy="Buy when RSI < 30 and volume increases 30%",
        days_back=30,
        symbols=["SOL", "ETH", "BTC"]
    )
    
    if result['passed']:
        print(f"✅ Strategy passed: {result['return']:.2f}% return")
    else:
        print(f"❌ Strategy failed: {result['return']:.2f}% return")
"""

import os
import sys
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_agent.data.pacifica_fetcher import PacificaDataFetcher
from llm_agent.data.indicator_calculator import IndicatorCalculator
from llm_agent.llm.model_client import ModelClient
from rbi_agent.cambrian_fetcher import CambrianDataFetcher

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyBacktester:
    """
    Backtesting engine for trading strategies
    
    Uses historical Cambrian data (multi-venue aggregated) for backtesting
    Falls back to Pacifica if Cambrian unavailable
    
    NOTE: This is separate from the live bot - RBI agent continues using Cambrian
    for historical backtesting even though live bot uses Pacifica only.
    """
    
    def __init__(self, use_cambrian: bool = True):
        """
        Initialize backtester
        
        Args:
            use_cambrian: Use Cambrian API (default: True) for multi-venue data
                         NOTE: Set to False only if Cambrian has persistent issues
        """
        self.use_cambrian = use_cambrian
        self.cambrian_fetcher = CambrianDataFetcher() if use_cambrian else None
        self.pacifica_fetcher = PacificaDataFetcher()  # Fallback
        self.indicator_calc = IndicatorCalculator()
    
    def fetch_historical_data(
        self, 
        symbol: str, 
        days_back: int = 30,
        interval: str = "15m"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data
        
        Args:
            symbol: Pacifica symbol (e.g., "SOL")
            days_back: Days of historical data to fetch
            interval: Candle interval ("15m", "1h", "4h", "1d")
            
        Returns:
            DataFrame with OHLCV + indicators, or None if fetch fails
        """
        try:
            # Calculate time range
            from datetime import datetime, timedelta
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)
            
            after_time = int(start_time.timestamp())  # Unix timestamp (seconds)
            before_time = int(end_time.timestamp())
            
            # Try Cambrian first (if enabled and symbol mapped)
            if self.use_cambrian and self.cambrian_fetcher:
                token_address = self.cambrian_fetcher.get_token_address(symbol)
                
                if token_address:
                    logger.info(f"Fetching {symbol} data from Cambrian ({days_back} days, {interval})...")
                    df = self.cambrian_fetcher.fetch_ohlcv(
                        token_address=token_address,
                        after_time=after_time,
                        before_time=before_time,
                        interval=interval
                    )
                    
                    if df is not None and not df.empty:
                        # Calculate indicators
                        df = self.indicator_calc.calculate_all_indicators(df)
                        logger.info(f"✅ Cambrian data: {len(df)} candles with indicators")
                        return df
                    else:
                        logger.warning(f"Cambrian fetch failed for {symbol}, falling back to Pacifica")
                else:
                    logger.warning(f"Token address not found for {symbol}, falling back to Pacifica")
            
            # Fallback to Pacifica
            logger.info(f"Fetching {symbol} data from Pacifica ({days_back} days, {interval})...")
            
            # Calculate limit based on interval
            if interval == "15m":
                limit = days_back * 96  # 96 candles per day
            elif interval == "1h":
                limit = days_back * 24
            elif interval == "4h":
                limit = days_back * 6
            elif interval == "1d":
                limit = days_back
            else:
                limit = days_back * 96  # Default to 15m
            
            # Fetch market data
            market_data = self.pacifica_fetcher.fetch_market_data(
                symbol=symbol,
                interval=interval,
                limit=min(limit, 1000)  # Pacifica API limit
            )
            
            if market_data is None or 'kline_df' not in market_data:
                logger.warning(f"No data returned for {symbol}")
                return None
            
            df = market_data['kline_df']
            
            if df is None or df.empty:
                logger.warning(f"Empty DataFrame for {symbol}")
                return None
            
            # Calculate indicators
            df = self.indicator_calc.calculate_all_indicators(df)
            logger.info(f"✅ Pacifica data: {len(df)} candles with indicators")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}", exc_info=True)
            return None
    
    def execute_strategy(
        self,
        df: pd.DataFrame,
        strategy_code: str,
        initial_capital: float = 1000.0
    ) -> Dict:
        """
        Execute strategy code on historical data
        
        Args:
            df: DataFrame with OHLCV + indicators
            strategy_code: Python code string implementing strategy
            initial_capital: Starting capital in USD
            
        Returns:
            Dict with backtest results:
                - return_pct: Total return %
                - win_rate: Win rate (0-1)
                - total_trades: Number of trades
                - sharpe_ratio: Sharpe ratio
                - max_drawdown: Maximum drawdown %
                - trades: List of trade dicts
        """
        try:
            # Prepare execution context
            exec_globals = {
                'pd': pd,
                'np': __import__('numpy'),
                'df': df.copy(),
                'initial_capital': initial_capital,
                'capital': initial_capital,
                'positions': [],
                'trades': []
            }
            
            # Strategy template - expects strategy_code to define buy/sell signals
            strategy_template = f"""
# Strategy code
{strategy_code}

# Execute strategy
position = None
entry_price = None
entry_index = None

for i in range(1, len(df)):
    # Get current signal from strategy
    signal = get_signal(df, i)
    current_price = df.iloc[i]['close']
    
    # Close position if we have one
    if position is not None:
        if signal == 'SELL' or signal == 'CLOSE' or signal is None:
            # Calculate P&L
            if position == 'LONG':
                pnl = (current_price - entry_price) / entry_price
            else:  # SHORT
                pnl = (entry_price - current_price) / entry_price
            
            pnl_usd = capital * pnl
            
            trades.append({{
                'entry_price': entry_price,
                'exit_price': current_price,
                'entry_time': df.iloc[entry_index]['timestamp'] if 'timestamp' in df.columns else entry_index,
                'exit_time': df.iloc[i]['timestamp'] if 'timestamp' in df.columns else i,
                'side': position,
                'pnl': pnl,
                'pnl_usd': pnl_usd
            }})
            
            capital = capital * (1 + pnl)
            position = None
            entry_price = None
    
    # Open new position
    if position is None and signal in ['BUY', 'SELL']:
        position = 'LONG' if signal == 'BUY' else 'SHORT'
        entry_price = current_price
        entry_index = i

# Close any open position at end
if position is not None:
    final_price = df.iloc[-1]['close']
    pnl = (final_price - entry_price) / entry_price if position == 'LONG' else (entry_price - final_price) / entry_price
    pnl_usd = capital * pnl
    
    trades.append({{
        'entry_price': entry_price,
        'exit_price': final_price,
        'entry_time': df.iloc[entry_index]['timestamp'] if 'timestamp' in df.columns else entry_index,
        'exit_time': df.iloc[-1]['timestamp'] if 'timestamp' in df.columns else len(df) - 1,
        'side': position,
        'pnl': pnl,
        'pnl_usd': pnl_usd
    }})
    
    capital = capital * (1 + pnl)

final_capital = capital
"""
            
            # Execute strategy
            exec(strategy_template, exec_globals)
            
            trades = exec_globals['trades']
            final_capital = exec_globals['final_capital']
            
            # Calculate metrics
            total_return = (final_capital - initial_capital) / initial_capital * 100
            total_trades = len(trades)
            
            if total_trades == 0:
                return {
                    'return_pct': 0.0,
                    'win_rate': 0.0,
                    'total_trades': 0,
                    'sharpe_ratio': 0.0,
                    'max_drawdown': 0.0,
                    'trades': []
                }
            
            winning_trades = [t for t in trades if t['pnl'] > 0]
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            
            # Calculate Sharpe ratio (simplified)
            if total_trades > 1:
                returns = [t['pnl'] for t in trades]
                avg_return = sum(returns) / len(returns)
                std_return = pd.Series(returns).std()
                sharpe_ratio = avg_return / std_return if std_return > 0 else 0
            else:
                sharpe_ratio = 0.0
            
            # Calculate max drawdown
            capital_curve = [initial_capital]
            for trade in trades:
                capital_curve.append(capital_curve[-1] * (1 + trade['pnl']))
            
            if len(capital_curve) > 1:
                peak = capital_curve[0]
                max_dd = 0.0
                for cap in capital_curve:
                    if cap > peak:
                        peak = cap
                    dd = (peak - cap) / peak * 100
                    if dd > max_dd:
                        max_dd = dd
            else:
                max_dd = 0.0
            
            return {
                'return_pct': total_return,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_dd,
                'final_capital': final_capital,
                'trades': trades
            }
            
        except Exception as e:
            logger.error(f"Error executing strategy: {e}", exc_info=True)
            return {
                'return_pct': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'error': str(e),
                'trades': []
            }


class RBIAgent:
    """
    Research-Based Inference Agent
    
    Takes trading strategy descriptions and:
    1. Uses LLM to generate backtest code
    2. Tests strategy on historical data
    3. Returns pass/fail with metrics
    """
    
    def __init__(
        self,
        deepseek_api_key: Optional[str] = None,
        model: str = "deepseek-chat"
    ):
        """
        Initialize RBI Agent
        
        Args:
            deepseek_api_key: DeepSeek API key (defaults to env var)
            model: Model to use for code generation
        """
        api_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DeepSeek API key required (DEEPSEEK_API_KEY env var or parameter)")
        
        self.model_client = ModelClient(
            api_key=api_key,
            model=model
        )
        self.backtester = StrategyBacktester()
        
        logger.info("✅ RBI Agent initialized")
    
    def generate_backtest_code(self, strategy_description: str) -> Optional[str]:
        """
        Generate Python backtest code from strategy description
        
        Args:
            strategy_description: Natural language strategy (e.g., "Buy when RSI < 30")
            
        Returns:
            Python code string implementing the strategy, or None if generation fails
        """
        prompt = f"""You are a trading strategy backtest code generator.

Strategy Description:
{strategy_description}

Your task: Generate Python code for a function `get_signal(df, i)` that returns:
- "BUY" when to enter a long position
- "SELL" when to enter a short position  
- "CLOSE" when to close current position
- None or "HOLD" when no action

The DataFrame `df` contains OHLCV data with these columns:
- open, high, low, close, volume
- rsi (RSI indicator)
- sma_20, sma_50 (moving averages)
- macd, macd_signal, macd_hist (MACD indicator)
- bbands_upper, bbands_middle, bbands_lower (Bollinger Bands)

The parameter `i` is the current index (row number).

Generate ONLY the function code, no explanations, no markdown:

def get_signal(df, i):
    # Your strategy logic here
    # Access data: df.iloc[i]['close'], df.iloc[i]['rsi'], etc.
    # Return: "BUY", "SELL", "CLOSE", or None
"""

        try:
            result = self.model_client.query(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3  # Lower temperature for more deterministic code
            )
            
            if result is None:
                logger.error("Failed to generate backtest code")
                return None
            
            code = result["content"].strip()
            
            # Clean up code (remove markdown if present)
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            
            logger.info(f"✅ Generated backtest code ({len(code)} chars)")
            return code
            
        except Exception as e:
            logger.error(f"Error generating backtest code: {e}")
            return None
    
    def test_strategy(
        self,
        strategy_description: str,
        symbols: List[str] = None,
        days_back: int = 30,
        min_return: float = 1.0,
        min_win_rate: float = 0.40,
        min_sharpe: float = 0.5
    ) -> Dict:
        """
        Test a trading strategy on historical data
        
        Args:
            strategy_description: Natural language strategy description
            symbols: List of symbols to test on (default: ["SOL", "ETH", "BTC"])
            days_back: Days of historical data to use
            min_return: Minimum return % to pass (default: 1.0%)
            min_win_rate: Minimum win rate to pass (default: 0.40)
            min_sharpe: Minimum Sharpe ratio to pass (default: 0.5)
            
        Returns:
            Dict with:
                - passed: bool
                - return_pct: Average return across symbols
                - win_rate: Average win rate
                - sharpe_ratio: Average Sharpe ratio
                - max_drawdown: Average max drawdown
                - total_trades: Total trades across all symbols
                - results_by_symbol: Dict of results per symbol
                - strategy_code: Generated Python code
        """
        if symbols is None:
            symbols = ["SOL", "ETH", "BTC"]
        
        logger.info(f"Testing strategy: {strategy_description}")
        logger.info(f"Symbols: {symbols}, Days: {days_back}")
        
        # Step 1: Generate backtest code
        strategy_code = self.generate_backtest_code(strategy_description)
        if strategy_code is None:
            return {
                'passed': False,
                'error': 'Failed to generate strategy code',
                'strategy_code': None
            }
        
        # Step 2: Test on each symbol
        results_by_symbol = {}
        all_results = []
        
        for symbol in symbols:
            logger.info(f"Testing on {symbol}...")
            
            # Fetch historical data
            df = self.backtester.fetch_historical_data(symbol, days_back=days_back)
            if df is None or df.empty:
                logger.warning(f"Skipping {symbol} - no data")
                continue
            
            # Execute strategy
            result = self.backtester.execute_strategy(df, strategy_code)
            
            if 'error' in result:
                logger.error(f"Error testing {symbol}: {result['error']}")
                continue
            
            results_by_symbol[symbol] = result
            all_results.append(result)
            
            logger.info(
                f"  {symbol}: Return={result['return_pct']:.2f}%, "
                f"Win Rate={result['win_rate']:.1%}, "
                f"Trades={result['total_trades']}"
            )
        
        if not all_results:
            return {
                'passed': False,
                'error': 'No valid results (all symbols failed)',
                'strategy_code': strategy_code
            }
        
        # Step 3: Calculate averages
        avg_return = sum(r['return_pct'] for r in all_results) / len(all_results)
        avg_win_rate = sum(r['win_rate'] for r in all_results) / len(all_results)
        avg_sharpe = sum(r['sharpe_ratio'] for r in all_results) / len(all_results)
        avg_max_dd = sum(r['max_drawdown'] for r in all_results) / len(all_results)
        total_trades = sum(r['total_trades'] for r in all_results)
        
        # Step 4: Determine if passed
        passed = (
            avg_return >= min_return and
            avg_win_rate >= min_win_rate and
            avg_sharpe >= min_sharpe and
            total_trades >= 5  # Minimum trades for valid test
        )
        
        result = {
            'passed': passed,
            'return_pct': avg_return,
            'win_rate': avg_win_rate,
            'sharpe_ratio': avg_sharpe,
            'max_drawdown': avg_max_dd,
            'total_trades': total_trades,
            'results_by_symbol': results_by_symbol,
            'strategy_code': strategy_code,
            'strategy_description': strategy_description
        }
        
        if passed:
            logger.info(f"✅ Strategy PASSED: {avg_return:.2f}% return, {avg_win_rate:.1%} win rate")
        else:
            logger.info(f"❌ Strategy FAILED: {avg_return:.2f}% return, {avg_win_rate:.1%} win rate")
        
        return result


def main():
    """Example usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RBI Agent - Strategy Backtesting")
    parser.add_argument("--strategy", type=str, required=True, help="Strategy description")
    parser.add_argument("--symbols", type=str, nargs="+", default=["SOL", "ETH", "BTC"], help="Symbols to test")
    parser.add_argument("--days", type=int, default=30, help="Days of historical data")
    parser.add_argument("--min-return", type=float, default=1.0, help="Minimum return % to pass")
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = RBIAgent()
    
    # Test strategy
    result = agent.test_strategy(
        strategy_description=args.strategy,
        symbols=args.symbols,
        days_back=args.days,
        min_return=args.min_return
    )
    
    # Print results
    print("\n" + "=" * 80)
    print("RBI BACKTEST RESULTS")
    print("=" * 80)
    print(f"Strategy: {result['strategy_description']}")
    print(f"Status: {'✅ PASSED' if result['passed'] else '❌ FAILED'}")
    print(f"Return: {result['return_pct']:.2f}%")
    print(f"Win Rate: {result['win_rate']:.1%}")
    print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {result['max_drawdown']:.2f}%")
    print(f"Total Trades: {result['total_trades']}")
    print("\nResults by Symbol:")
    for symbol, symbol_result in result['results_by_symbol'].items():
        print(f"  {symbol}: {symbol_result['return_pct']:.2f}% return, "
              f"{symbol_result['win_rate']:.1%} win rate, "
              f"{symbol_result['total_trades']} trades")
    print("=" * 80)


if __name__ == "__main__":
    main()

