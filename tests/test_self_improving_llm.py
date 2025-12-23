"""
Tests for Self-Improving LLM Strategy

Tests the multi-dimensional learning system for single-asset trading.
"""

import os
import sys
import json
import tempfile
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategies.self_improving_llm import (
    OutcomeTracker,
    PerformanceAnalyzer,
    StrategyAdjuster,
    SelfImprovingLLMStrategy,
    StrategyConfig
)
from core.strategies.self_improving_llm.performance_analyzer import ActionType


class TestOutcomeTracker:
    """Test OutcomeTracker functionality"""

    def test_record_entry(self):
        """Test recording a trade entry"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)

            trade_id = tracker.record_entry(
                symbol="SOL/USDT-P",
                direction="LONG",
                confidence=0.75,
                entry_price=150.0,
                llm_reasoning="Strong momentum"
            )

            assert trade_id == 1
            assert tracker.get_trade_count() == 0  # Still open

            # Check open trade
            open_trades = tracker.get_open_trades()
            assert len(open_trades) == 1
            assert open_trades[0]["symbol"] == "SOL/USDT-P"
            assert open_trades[0]["direction"] == "LONG"
        finally:
            os.unlink(temp_file)

    def test_record_exit_win(self):
        """Test recording a winning trade exit"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)

            trade_id = tracker.record_entry(
                symbol="BTC/USDT-P",
                direction="LONG",
                confidence=0.8,
                entry_price=100000.0
            )

            outcome = tracker.record_exit(
                trade_id=trade_id,
                exit_price=101000.0,  # 1% gain
                pnl_usd=5.0
            )

            assert outcome is not None
            assert outcome["is_win"] == True
            assert outcome["pnl_percent"] > 0
            assert tracker.get_trade_count() == 1
        finally:
            os.unlink(temp_file)

    def test_record_exit_loss(self):
        """Test recording a losing trade exit"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)

            trade_id = tracker.record_entry(
                symbol="ETH/USDT-P",
                direction="SHORT",
                confidence=0.6,
                entry_price=3000.0
            )

            outcome = tracker.record_exit(
                trade_id=trade_id,
                exit_price=3100.0,  # Price went up = loss on short
                pnl_usd=-2.0
            )

            assert outcome is not None
            assert outcome["is_win"] == False
            assert outcome["pnl_percent"] < 0
        finally:
            os.unlink(temp_file)

    def test_stats_by_dimension(self):
        """Test statistics grouped by dimension"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)

            # Record multiple trades
            symbols = ["SOL/USDT-P", "SOL/USDT-P", "BTC/USDT-P", "BTC/USDT-P"]
            directions = ["LONG", "SHORT", "LONG", "LONG"]
            wins = [True, False, True, True]

            for i, (sym, dir, win) in enumerate(zip(symbols, directions, wins)):
                trade_id = tracker.record_entry(
                    symbol=sym,
                    direction=dir,
                    confidence=0.7,
                    entry_price=100.0
                )
                exit_price = 105.0 if (dir == "LONG" and win) or (dir == "SHORT" and not win) else 95.0
                tracker.record_exit(trade_id=trade_id, exit_price=exit_price, pnl_usd=1.0 if win else -1.0)

            # Test by symbol
            symbol_stats = tracker.get_stats_by_dimension("symbol")
            assert "SOL" in symbol_stats
            assert "BTC" in symbol_stats
            assert symbol_stats["SOL"]["count"] == 2
            assert symbol_stats["BTC"]["count"] == 2

            # Test by direction
            direction_stats = tracker.get_stats_by_dimension("direction")
            assert "LONG" in direction_stats
            assert "SHORT" in direction_stats
            assert direction_stats["LONG"]["count"] == 3
            assert direction_stats["SHORT"]["count"] == 1
        finally:
            os.unlink(temp_file)

    def test_combo_stats(self):
        """Test statistics for symbol+direction combos"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)

            # Record SOL_SHORT trades (2 trades, 0 wins)
            for _ in range(2):
                trade_id = tracker.record_entry(
                    symbol="SOL/USDT-P",
                    direction="SHORT",
                    confidence=0.6,
                    entry_price=100.0
                )
                tracker.record_exit(trade_id=trade_id, exit_price=105.0, pnl_usd=-1.0)

            # Record BTC_LONG trades (3 trades, 2 wins)
            for i in range(3):
                trade_id = tracker.record_entry(
                    symbol="BTC/USDT-P",
                    direction="LONG",
                    confidence=0.7,
                    entry_price=100.0
                )
                win = i < 2  # First 2 are wins
                exit_price = 105.0 if win else 95.0
                tracker.record_exit(trade_id=trade_id, exit_price=exit_price, pnl_usd=1.0 if win else -1.0)

            combo_stats = tracker.get_combo_stats()
            assert "SOL_SHORT" in combo_stats
            assert "BTC_LONG" in combo_stats
            assert combo_stats["SOL_SHORT"]["win_rate"] == 0.0
            assert abs(combo_stats["BTC_LONG"]["win_rate"] - 0.6667) < 0.01
        finally:
            os.unlink(temp_file)


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer functionality"""

    def test_analyze_insufficient_data(self):
        """Test analysis with insufficient data"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)
            analyzer = PerformanceAnalyzer()

            # Only 2 trades
            for i in range(2):
                trade_id = tracker.record_entry(symbol="SOL/USDT-P", direction="LONG", confidence=0.7, entry_price=100.0)
                tracker.record_exit(trade_id=trade_id, exit_price=105.0, pnl_usd=1.0)

            report = analyzer.analyze(tracker)
            assert report.sufficient_data == False
            assert len(report.top_issues) == 0
        finally:
            os.unlink(temp_file)

    def test_analyze_identifies_bad_performer(self):
        """Test that analyzer identifies poor performers"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)
            analyzer = PerformanceAnalyzer()

            # Create 10 SOL_SHORT trades with 20% win rate (terrible)
            for i in range(10):
                trade_id = tracker.record_entry(
                    symbol="SOL/USDT-P",
                    direction="SHORT",
                    confidence=0.6,
                    entry_price=100.0
                )
                win = i < 2  # Only 2/10 wins
                exit_price = 95.0 if win else 105.0  # SHORT profits when price drops
                tracker.record_exit(trade_id=trade_id, exit_price=exit_price, pnl_usd=1.0 if win else -2.0)

            # Add some good trades to hit minimum
            for i in range(5):
                trade_id = tracker.record_entry(
                    symbol="BTC/USDT-P",
                    direction="LONG",
                    confidence=0.8,
                    entry_price=100.0
                )
                tracker.record_exit(trade_id=trade_id, exit_price=105.0, pnl_usd=1.0)

            report = analyzer.analyze(tracker)
            assert report.sufficient_data == True

            # Should identify SOL_SHORT as an issue
            issue_keys = [issue.key for issue in report.top_issues]
            assert "SOL_SHORT" in issue_keys or "SHORT" in issue_keys or "SOL" in issue_keys
        finally:
            os.unlink(temp_file)

    def test_get_filters_from_report(self):
        """Test extracting filters from analysis report"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            tracker = OutcomeTracker(log_file=temp_file)
            analyzer = PerformanceAnalyzer()

            # Create poor performing combo
            for i in range(12):
                trade_id = tracker.record_entry(
                    symbol="SOL/USDT-P",
                    direction="SHORT",
                    confidence=0.5,
                    entry_price=100.0
                )
                win = i < 2  # 2/12 = 16.7% win rate
                exit_price = 95.0 if win else 105.0
                tracker.record_exit(trade_id=trade_id, exit_price=exit_price, pnl_usd=1.0 if win else -2.0)

            report = analyzer.analyze(tracker)
            filters = analyzer.get_filters_from_report(report)

            # Should generate at least one filter
            assert len(filters) > 0
            assert any(f["action"] in ["block", "reduce"] for f in filters)
        finally:
            os.unlink(temp_file)


class TestStrategyAdjuster:
    """Test StrategyAdjuster functionality"""

    def test_add_and_apply_block_filter(self):
        """Test adding and applying a block filter"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            adjuster = StrategyAdjuster(state_file=temp_file)

            # Add block filter for SOL_SHORT
            adjuster.add_filter(
                filter_type="block",
                dimension="combo",
                key="SOL_SHORT",
                action_value=1.0,
                reason="20% win rate"
            )

            # Test that it blocks
            decision = {"symbol": "SOL/USDT-P", "action": "SHORT", "confidence": 0.8}
            modified, rejection = adjuster.apply_filters(decision)

            assert rejection is not None
            assert "BLOCKED" in rejection
        finally:
            os.unlink(temp_file)

    def test_apply_reduce_filter(self):
        """Test applying a position size reduction filter"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            adjuster = StrategyAdjuster(state_file=temp_file)

            # Add reduce filter for SOL
            adjuster.add_filter(
                filter_type="reduce",
                dimension="symbol",
                key="SOL",
                action_value=0.5,
                reason="35% win rate"
            )

            # Test that it reduces
            decision = {"symbol": "SOL/USDT-P", "action": "LONG", "confidence": 0.8, "position_size_usd": 10.0}
            modified, rejection = adjuster.apply_filters(decision)

            assert rejection is None  # Not blocked
            assert modified["position_size_usd"] == 5.0  # Reduced 50%
        finally:
            os.unlink(temp_file)

    def test_confidence_threshold_filter(self):
        """Test confidence threshold filter"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            adjuster = StrategyAdjuster(state_file=temp_file)

            # Add confidence threshold for SHORT
            adjuster.add_filter(
                filter_type="confidence_threshold",
                dimension="direction",
                key="SHORT",
                action_value=0.9,
                reason="Require high confidence for shorts"
            )

            # Test low confidence rejection
            decision1 = {"symbol": "BTC/USDT-P", "action": "SHORT", "confidence": 0.7}
            _, rejection1 = adjuster.apply_filters(decision1)
            assert rejection1 is not None

            # Test high confidence acceptance
            decision2 = {"symbol": "BTC/USDT-P", "action": "SHORT", "confidence": 0.95}
            _, rejection2 = adjuster.apply_filters(decision2)
            assert rejection2 is None
        finally:
            os.unlink(temp_file)

    def test_prompt_context_generation(self):
        """Test generating prompt context"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            adjuster = StrategyAdjuster(state_file=temp_file)

            # Add various filters
            adjuster.add_filter(
                filter_type="block",
                dimension="combo",
                key="SOL_SHORT",
                action_value=1.0,
                reason="20% win rate",
                source_stats={"win_rate": 0.2, "total_pnl": -15.0}
            )

            context = adjuster.get_prompt_context()

            assert "PERFORMANCE ALERTS" in context
            assert "BLOCKED" in context
            assert "SOL_SHORT" in context
        finally:
            os.unlink(temp_file)


class TestSelfImprovingLLMStrategy:
    """Test the main orchestrating strategy"""

    def test_full_workflow(self):
        """Test complete trade lifecycle"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                review_interval=5,
                min_trades_for_analysis=5,
                rolling_window=20,
                auto_apply_filters=True,
                log_dir=temp_dir
            )

            strategy = SelfImprovingLLMStrategy(config=config)

            # Record 5 losing SOL_SHORT trades
            for i in range(5):
                trade_id = strategy.record_trade_entry(
                    symbol="SOL/USDT-P",
                    direction="SHORT",
                    confidence=0.6,
                    entry_price=100.0
                )
                strategy.record_trade_exit(
                    trade_id=trade_id,
                    exit_price=105.0,  # Loss on short
                    pnl_usd=-2.0
                )

            # Add 5 winning BTC_LONG trades
            for i in range(5):
                trade_id = strategy.record_trade_entry(
                    symbol="BTC/USDT-P",
                    direction="LONG",
                    confidence=0.8,
                    entry_price=100.0
                )
                strategy.record_trade_exit(
                    trade_id=trade_id,
                    exit_price=105.0,
                    pnl_usd=2.0
                )

            # Check stats
            stats = strategy.get_stats()
            assert stats["total_trades"] == 10

            # Get dimension breakdown
            breakdown = strategy.get_dimension_breakdown()
            assert "by_symbol" in breakdown
            assert "by_direction" in breakdown
            assert "by_combo" in breakdown

    def test_filter_integration(self):
        """Test that filters are applied after analysis"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = StrategyConfig(
                review_interval=5,
                min_trades_for_analysis=5,
                rolling_window=20,
                auto_apply_filters=True,
                log_dir=temp_dir
            )

            strategy = SelfImprovingLLMStrategy(config=config)

            # Create 10 terrible SOL_SHORT trades (0% win rate)
            for i in range(10):
                trade_id = strategy.record_trade_entry(
                    symbol="SOL/USDT-P",
                    direction="SHORT",
                    confidence=0.5,
                    entry_price=100.0
                )
                strategy.record_trade_exit(
                    trade_id=trade_id,
                    exit_price=110.0,  # Big loss on short
                    pnl_usd=-5.0
                )

            # Add some good trades
            for i in range(5):
                trade_id = strategy.record_trade_entry(
                    symbol="BTC/USDT-P",
                    direction="LONG",
                    confidence=0.8,
                    entry_price=100.0
                )
                strategy.record_trade_exit(
                    trade_id=trade_id,
                    exit_price=105.0,
                    pnl_usd=2.0
                )

            # Force a review to apply filters
            strategy.force_review()

            # Check that SOL_SHORT would be filtered
            decision = {"symbol": "SOL/USDT-P", "action": "SHORT", "confidence": 0.6}
            modified, rejection = strategy.filter_decision(decision)

            # Should either be blocked or have reduced size
            stats = strategy.get_stats()
            assert stats["active_filters"] > 0 or rejection is not None


class TestHibachiStrategyF:
    """Test the Hibachi adapter"""

    def test_strategy_f_init(self):
        """Test Strategy F initialization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            from hibachi_agent.execution.strategy_f_self_improving import StrategyFSelfImproving

            strategy = StrategyFSelfImproving(
                position_size=10.0,
                review_interval=10,
                log_dir=temp_dir
            )

            assert strategy.position_size == 10.0
            stats = strategy.get_stats()
            assert "total_trades" in stats

    def test_strategy_f_trade_lifecycle(self):
        """Test Strategy F trade recording"""
        with tempfile.TemporaryDirectory() as temp_dir:
            from hibachi_agent.execution.strategy_f_self_improving import StrategyFSelfImproving

            strategy = StrategyFSelfImproving(
                position_size=10.0,
                log_dir=temp_dir
            )

            decision = {
                "symbol": "SOL/USDT-P",
                "action": "LONG",
                "confidence": 0.75,
                "reasoning": "Test trade"
            }

            # Record entry
            trade_id = strategy.record_entry(decision, entry_price=150.0)
            assert trade_id == 1

            # Verify active trade tracking
            assert strategy.get_active_trade_id("SOL/USDT-P") == 1

            # Record exit
            outcome = strategy.record_exit(symbol="SOL/USDT-P", exit_price=152.0, pnl_usd=1.50)
            assert outcome is not None
            assert outcome["is_win"] == True

            # Verify trade tracking cleared
            assert strategy.get_active_trade_id("SOL/USDT-P") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
