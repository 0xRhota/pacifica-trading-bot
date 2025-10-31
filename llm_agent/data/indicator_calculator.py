"""
Technical Indicators Calculator
Calculates technical indicators using the `ta` library (NOT pandas_ta)

Usage:
    calculator = IndicatorCalculator()
    df_with_indicators = calculator.calculate_all_indicators(kline_df)
"""

import pandas as pd
import logging
from typing import Optional
import ta  # Using ta library (NOT pandas_ta per PRD)

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Calculate technical indicators for market data"""

    def __init__(self):
        """Initialize indicator calculator"""
        pass

    def calculate_sma(
        self,
        df: pd.DataFrame,
        period: int = 20,
        column: str = "close"
    ) -> pd.Series:
        """
        Calculate Simple Moving Average

        Args:
            df: DataFrame with OHLCV data
            period: SMA period (default: 20)
            column: Column to calculate SMA on (default: close)

        Returns:
            Series with SMA values
        """
        return ta.trend.sma_indicator(df[column], window=period)

    def calculate_rsi(
        self,
        df: pd.DataFrame,
        period: int = 14,
        column: str = "close"
    ) -> pd.Series:
        """
        Calculate Relative Strength Index

        Args:
            df: DataFrame with OHLCV data
            period: RSI period (default: 14)
            column: Column to calculate RSI on (default: close)

        Returns:
            Series with RSI values (0-100)
        """
        return ta.momentum.rsi(df[column], window=period)

    def calculate_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = "close"
    ) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence)

        Args:
            df: DataFrame with OHLCV data
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)
            column: Column to calculate MACD on (default: close)

        Returns:
            DataFrame with columns: macd, macd_signal, macd_diff
        """
        macd = ta.trend.MACD(
            df[column],
            window_slow=slow,
            window_fast=fast,
            window_sign=signal
        )

        return pd.DataFrame({
            "macd": macd.macd(),
            "macd_signal": macd.macd_signal(),
            "macd_diff": macd.macd_diff()
        })

    def calculate_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
        column: str = "close"
    ) -> pd.DataFrame:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with OHLCV data
            period: Moving average period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)
            column: Column to calculate bands on (default: close)

        Returns:
            DataFrame with columns: bb_upper, bb_middle, bb_lower, bb_width
        """
        bb = ta.volatility.BollingerBands(
            df[column],
            window=period,
            window_dev=std_dev
        )

        return pd.DataFrame({
            "bb_upper": bb.bollinger_hband(),
            "bb_middle": bb.bollinger_mavg(),
            "bb_lower": bb.bollinger_lband(),
            "bb_width": bb.bollinger_wband()
        })

    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all indicators for a DataFrame

        Args:
            df: DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)

        Returns:
            DataFrame with all indicators added
        """
        if df is None or df.empty:
            logger.warning("Cannot calculate indicators on empty DataFrame")
            return df

        try:
            # Make a copy to avoid modifying original
            result = df.copy()

            # SMA (20 and 50 periods)
            result['sma_20'] = self.calculate_sma(df, period=20)
            result['sma_50'] = self.calculate_sma(df, period=50)

            # Check if SMA20 > SMA50 (trend indicator)
            result['sma_20_above_50'] = result['sma_20'] > result['sma_50']

            # RSI (14 period)
            result['rsi'] = self.calculate_rsi(df, period=14)

            # MACD
            macd_df = self.calculate_macd(df)
            result['macd'] = macd_df['macd']
            result['macd_signal'] = macd_df['macd_signal']
            result['macd_diff'] = macd_df['macd_diff']

            # Bollinger Bands (20 period, 2 std dev)
            bb_df = self.calculate_bollinger_bands(df, period=20, std_dev=2.0)
            result['bb_upper'] = bb_df['bb_upper']
            result['bb_middle'] = bb_df['bb_middle']
            result['bb_lower'] = bb_df['bb_lower']
            result['bb_width'] = bb_df['bb_width']

            # Additional derived indicators
            # Price position within Bollinger Bands (0-1 scale)
            result['bb_position'] = (
                (result['close'] - result['bb_lower']) /
                (result['bb_upper'] - result['bb_lower'])
            ).clip(0, 1)

            logger.info(f"✅ Calculated indicators for {len(result)} candles")
            return result

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

    def get_latest_values(self, df: pd.DataFrame) -> dict:
        """
        Extract latest indicator values for LLM prompt

        Args:
            df: DataFrame with indicators calculated

        Returns:
            Dict with latest indicator values
        """
        if df is None or df.empty:
            return {}

        latest = df.iloc[-1]

        return {
            "price": latest.get('close'),
            "sma_20": latest.get('sma_20'),
            "sma_50": latest.get('sma_50'),
            "sma_20_above_50": latest.get('sma_20_above_50'),
            "rsi": latest.get('rsi'),
            "macd": latest.get('macd'),
            "macd_signal": latest.get('macd_signal'),
            "macd_diff": latest.get('macd_diff'),
            "bb_upper": latest.get('bb_upper'),
            "bb_middle": latest.get('bb_middle'),
            "bb_lower": latest.get('bb_lower'),
            "bb_position": latest.get('bb_position')
        }
