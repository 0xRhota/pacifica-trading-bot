"""
Comprehensive Test Suite for Self-Improving Pairs Trade Strategy

Tests all components:
1. OutcomeTracker - Recording and analyzing trade outcomes
2. PerformanceAnalyzer - Generating recommendations
3. StrategyAdjuster - Gradual bias adjustments
4. SelfImprovingPairsStrategy - Integration tests

Run with: python -m pytest tests/test_self_improving_pairs.py -v
"""

import pytest
import json
import os
import tempfile
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategies.self_improving_pairs.outcome_tracker import OutcomeTracker
from core.strategies.self_improving_pairs.performance_analyzer import (
    PerformanceAnalyzer, Recommendation, AnalysisResult
)
from core.strategies.self_improving_pairs.strategy_adjuster import StrategyAdjuster
from core.strategies.self_improving_pairs.strategy import SelfImprovingPairsStrategy


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def temp_state_file():
    """Create a temporary state file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def outcome_tracker(temp_log_file):
    """Create an OutcomeTracker with temp file"""
    return OutcomeTracker(log_file=temp_log_file)


@pytest.fixture
def analyzer():
    """Create a PerformanceAnalyzer"""
    return PerformanceAnalyzer()


@pytest.fixture
def adjuster(temp_state_file):
    """Create a StrategyAdjuster with temp file"""
    return StrategyAdjuster(state_file=temp_state_file)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    mock = Mock()
    mock.query = Mock(return_value={
        'content': 'LONG: ETH-USD\nSHORT: BTC-USD\nCONFIDENCE: 0.7\nREASON: Test reasoning'
    })
    return mock


# ============================================================================
# OUTCOME TRACKER TESTS
# ============================================================================

class TestOutcomeTracker:
    """Tests for OutcomeTracker class"""

    def test_initialization(self, outcome_tracker):
        """Test tracker initializes correctly"""
        assert outcome_tracker is not None
        assert outcome_tracker.get_trade_count() == 0

    def test_record_entry(self, outcome_tracker):
        """Test recording a trade entry"""
        trade_id = outcome_tracker.record_entry(
            long_symbol="ETH-USD",
            short_symbol="BTC-USD",
            entry_prices={"ETH-USD": 3000.0, "BTC-USD": 90000.0},
            llm_reasoning="Test reasoning"
        )

        assert trade_id == 1
        assert outcome_tracker.get_open_trade() is not None

    def test_record_exit_correct_direction(self, outcome_tracker):
        """Test recording exit when direction was correct (long outperformed)"""
        # Entry
        trade_id = outcome_tracker.record_entry(
            long_symbol="ETH-USD",
            short_symbol="BTC-USD",
            entry_prices={"ETH-USD": 3000.0, "BTC-USD": 90000.0},
            llm_reasoning="Test"
        )

        # Exit - ETH went up 5%, BTC went up 2%
        # Long ETH: +5%, Short BTC: -2% (we lose because BTC went up)
        # But direction was correct because ETH outperformed BTC
        outcome = outcome_tracker.record_exit(
            trade_id=trade_id,
            exit_prices={"ETH-USD": 3150.0, "BTC-USD": 91800.0}  # ETH +5%, BTC +2%
        )

        assert outcome is not None
        assert outcome["correct_direction"] == True  # ETH outperformed
        assert outcome["long_return"] == pytest.approx(5.0, rel=0.01)

    def test_record_exit_wrong_direction(self, outcome_tracker):
        """Test recording exit when direction was wrong (short outperformed)"""
        trade_id = outcome_tracker.record_entry(
            long_symbol="ETH-USD",
            short_symbol="BTC-USD",
            entry_prices={"ETH-USD": 3000.0, "BTC-USD": 90000.0},
            llm_reasoning="Test"
        )

        # Exit - ETH went up 1%, BTC went up 5%
        # Direction was wrong because BTC outperformed ETH
        outcome = outcome_tracker.record_exit(
            trade_id=trade_id,
            exit_prices={"ETH-USD": 3030.0, "BTC-USD": 94500.0}  # ETH +1%, BTC +5%
        )

        assert outcome is not None
        assert outcome["correct_direction"] == False  # BTC outperformed

    def test_rolling_stats_empty(self, outcome_tracker):
        """Test rolling stats with no trades"""
        stats = outcome_tracker.get_rolling_stats(n=10)

        assert stats["total"] == 0
        assert stats["accuracy"] == 0.0
        assert stats["sufficient_data"] == False

    def test_rolling_stats_with_trades(self, outcome_tracker):
        """Test rolling stats with multiple trades"""
        # Record 6 trades: 4 correct, 2 wrong
        trades_data = [
            (True, {"ETH-USD": 3000, "BTC-USD": 90000}, {"ETH-USD": 3150, "BTC-USD": 90900}),  # ETH +5%, BTC +1%
            (True, {"ETH-USD": 3000, "BTC-USD": 90000}, {"ETH-USD": 3090, "BTC-USD": 90000}),  # ETH +3%, BTC 0%
            (False, {"ETH-USD": 3000, "BTC-USD": 90000}, {"ETH-USD": 3000, "BTC-USD": 94500}),  # ETH 0%, BTC +5%
            (True, {"ETH-USD": 3000, "BTC-USD": 90000}, {"ETH-USD": 3060, "BTC-USD": 90000}),  # ETH +2%, BTC 0%
            (False, {"ETH-USD": 3000, "BTC-USD": 90000}, {"ETH-USD": 2970, "BTC-USD": 89100}),  # ETH -1%, BTC -1%
            (True, {"ETH-USD": 3000, "BTC-USD": 90000}, {"ETH-USD": 3120, "BTC-USD": 90900}),  # ETH +4%, BTC +1%
        ]

        for expected_correct, entry, exit_p in trades_data:
            tid = outcome_tracker.record_entry(
                long_symbol="ETH-USD",
                short_symbol="BTC-USD",
                entry_prices=entry,
                llm_reasoning="Test"
            )
            outcome_tracker.record_exit(tid, exit_p)

        stats = outcome_tracker.get_rolling_stats(n=10)

        assert stats["total"] == 6
        assert stats["correct"] == 4
        assert stats["accuracy"] == pytest.approx(4/6, rel=0.01)
        assert stats["sufficient_data"] == True

    def test_persistence(self, temp_log_file):
        """Test that data persists across instances"""
        # Create tracker and record trade
        tracker1 = OutcomeTracker(log_file=temp_log_file)
        trade_id = tracker1.record_entry(
            long_symbol="ETH-USD",
            short_symbol="BTC-USD",
            entry_prices={"ETH-USD": 3000.0, "BTC-USD": 90000.0},
            llm_reasoning="Test"
        )
        tracker1.record_exit(trade_id, {"ETH-USD": 3100.0, "BTC-USD": 90000.0})

        # Create new tracker instance
        tracker2 = OutcomeTracker(log_file=temp_log_file)

        assert tracker2.get_trade_count() == 1


# ============================================================================
# PERFORMANCE ANALYZER TESTS
# ============================================================================

class TestPerformanceAnalyzer:
    """Tests for PerformanceAnalyzer class"""

    def test_initialization(self, analyzer):
        """Test analyzer initializes correctly"""
        assert analyzer is not None
        assert analyzer.ACCURACY_TERRIBLE == 0.35
        assert analyzer.ACCURACY_GOOD == 0.55

    def test_analyze_insufficient_data(self, analyzer):
        """Test analysis with insufficient data"""
        stats = {"total": 3, "correct": 2, "accuracy": 0.67, "sufficient_data": False}

        result = analyzer.analyze(stats)

        assert result.recommendation == Recommendation.INSUFFICIENT_DATA
        assert result.suggested_bias == 0.5

    def test_analyze_good_accuracy(self, analyzer):
        """Test analysis with good accuracy"""
        stats = {
            "total": 10,
            "correct": 7,
            "accuracy": 0.70,
            "avg_spread_return": 0.5,
            "eth_bias": {"count": 5, "correct": 4, "accuracy": 0.8},
            "btc_bias": {"count": 5, "correct": 3, "accuracy": 0.6},
            "sufficient_data": True
        }

        result = analyzer.analyze(stats)

        assert result.recommendation == Recommendation.HOLD_STEADY
        assert result.accuracy == 0.70

    def test_analyze_terrible_accuracy_eth_bias(self, analyzer):
        """Test analysis with terrible ETH accuracy"""
        stats = {
            "total": 10,
            "correct": 2,
            "accuracy": 0.20,
            "avg_spread_return": -1.5,
            "eth_bias": {"count": 8, "correct": 1, "accuracy": 0.125},
            "btc_bias": {"count": 2, "correct": 1, "accuracy": 0.5},
            "sufficient_data": True
        }

        result = analyzer.analyze(stats)

        assert result.recommendation == Recommendation.INCREASE_BTC_BIAS
        assert result.suggested_bias > 0.5  # Should lean BTC

    def test_analyze_terrible_accuracy_btc_bias(self, analyzer):
        """Test analysis with terrible BTC accuracy"""
        stats = {
            "total": 10,
            "correct": 2,
            "accuracy": 0.20,
            "avg_spread_return": -1.5,
            "eth_bias": {"count": 2, "correct": 1, "accuracy": 0.5},
            "btc_bias": {"count": 8, "correct": 1, "accuracy": 0.125},
            "sufficient_data": True
        }

        result = analyzer.analyze(stats)

        assert result.recommendation == Recommendation.INCREASE_ETH_BIAS
        assert result.suggested_bias < 0.5  # Should lean ETH

    def test_should_trigger_adjustment(self, analyzer):
        """Test trigger adjustment logic"""
        # Should trigger
        result1 = AnalysisResult(
            accuracy=0.30,
            sample_size=10,
            recommendation=Recommendation.INCREASE_BTC_BIAS,
            suggested_bias=0.7,
            reasoning="Test",
            eth_accuracy=0.25,
            btc_accuracy=0.50,
            avg_spread_return=-0.5,
            confidence=0.8
        )
        assert analyzer.should_trigger_adjustment(result1) == True

        # Should NOT trigger (hold steady)
        result2 = AnalysisResult(
            accuracy=0.60,
            sample_size=10,
            recommendation=Recommendation.HOLD_STEADY,
            suggested_bias=0.5,
            reasoning="Test",
            eth_accuracy=0.60,
            btc_accuracy=0.60,
            avg_spread_return=0.3,
            confidence=0.7
        )
        assert analyzer.should_trigger_adjustment(result2) == False


# ============================================================================
# STRATEGY ADJUSTER TESTS
# ============================================================================

class TestStrategyAdjuster:
    """Tests for StrategyAdjuster class"""

    def test_initialization(self, adjuster):
        """Test adjuster initializes with neutral bias"""
        assert adjuster.get_current_bias() == 0.5

    def test_get_bias_instruction_neutral(self, adjuster):
        """Test neutral bias instruction"""
        instruction = adjuster.get_bias_instruction()
        assert "NEUTRAL" in instruction

    def test_adjust_toward_btc(self, adjuster):
        """Test adjustment toward BTC"""
        analysis = AnalysisResult(
            accuracy=0.25,
            sample_size=10,
            recommendation=Recommendation.INCREASE_BTC_BIAS,
            suggested_bias=0.75,
            reasoning="ETH calls underperforming",
            eth_accuracy=0.20,
            btc_accuracy=0.50,
            avg_spread_return=-1.0,
            confidence=0.8
        )

        new_bias = adjuster.adjust(analysis, current_trade_count=10)

        assert new_bias > 0.5
        assert new_bias <= 0.65  # Max adjustment is 0.15

    def test_adjust_toward_eth(self, adjuster):
        """Test adjustment toward ETH"""
        # First set bias to BTC
        adjuster._state["current_bias"] = 0.7
        adjuster._save_state()

        analysis = AnalysisResult(
            accuracy=0.25,
            sample_size=10,
            recommendation=Recommendation.INCREASE_ETH_BIAS,
            suggested_bias=0.3,
            reasoning="BTC calls underperforming",
            eth_accuracy=0.50,
            btc_accuracy=0.20,
            avg_spread_return=-1.0,
            confidence=0.8
        )

        new_bias = adjuster.adjust(analysis, current_trade_count=15)

        assert new_bias < 0.7
        assert new_bias >= 0.54  # Max adjustment is 0.15 (allow float precision)

    def test_bias_clamped_to_range(self, adjuster):
        """Test that bias stays within valid range"""
        # Try to push beyond max
        adjuster._state["current_bias"] = 0.80

        analysis = AnalysisResult(
            accuracy=0.20,
            sample_size=10,
            recommendation=Recommendation.INCREASE_BTC_BIAS,
            suggested_bias=0.95,
            reasoning="Test",
            eth_accuracy=0.15,
            btc_accuracy=0.30,
            avg_spread_return=-2.0,
            confidence=0.9
        )

        new_bias = adjuster.adjust(analysis, current_trade_count=20)

        assert new_bias <= adjuster.MAX_BIAS  # Should be clamped to 0.85

    def test_reset_to_neutral(self, adjuster):
        """Test resetting to neutral"""
        adjuster._state["current_bias"] = 0.75
        adjuster._save_state()

        adjuster.reset_to_neutral("Testing reset")

        assert adjuster.get_current_bias() == 0.5

    def test_adjustment_history(self, adjuster):
        """Test that adjustments are logged"""
        analysis = AnalysisResult(
            accuracy=0.30,
            sample_size=10,
            recommendation=Recommendation.INCREASE_BTC_BIAS,
            suggested_bias=0.70,
            reasoning="Test adjustment",
            eth_accuracy=0.25,
            btc_accuracy=0.50,
            avg_spread_return=-0.8,
            confidence=0.7
        )

        adjuster.adjust(analysis, current_trade_count=10)

        history = adjuster.get_adjustment_history(n=5)
        assert len(history) >= 1
        assert history[-1]["reasoning"] == "Test adjustment"

    def test_persistence(self, temp_state_file):
        """Test that state persists across instances"""
        adjuster1 = StrategyAdjuster(state_file=temp_state_file)
        adjuster1._state["current_bias"] = 0.65
        adjuster1._save_state()

        adjuster2 = StrategyAdjuster(state_file=temp_state_file)
        assert adjuster2.get_current_bias() == 0.65


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestSelfImprovingPairsStrategy:
    """Integration tests for the main strategy class"""

    @pytest.fixture
    def strategy(self, temp_log_file, temp_state_file, mock_llm_client):
        """Create a strategy with temp files"""
        # Patch the default file paths
        with patch.object(OutcomeTracker, 'DEFAULT_LOG_FILE', temp_log_file):
            with patch.object(StrategyAdjuster, 'STATE_FILE', temp_state_file):
                return SelfImprovingPairsStrategy(
                    asset_a="ETH-USD",
                    asset_b="BTC-USD",
                    llm_client=mock_llm_client,
                    hold_time_seconds=3600
                )

    def test_initialization(self, strategy):
        """Test strategy initializes correctly"""
        assert strategy.asset_a == "ETH-USD"
        assert strategy.asset_b == "BTC-USD"
        assert strategy.hold_time_seconds == 3600
        assert not strategy.has_active_trade()

    def test_get_decisions(self, strategy):
        """Test getting trading decisions"""
        import asyncio
        market_data = {
            "ETH-USD": {"price": 3000, "rsi": 45, "macd": 10, "price_change_24h": 2.5},
            "BTC-USD": {"price": 90000, "rsi": 55, "macd": 500, "price_change_24h": 1.5}
        }

        decisions = asyncio.get_event_loop().run_until_complete(
            strategy.get_decisions(market_data, position_size_usd=10)
        )

        assert len(decisions) == 2
        assert decisions[0]["action"] == "LONG"
        assert decisions[1]["action"] == "SHORT"
        assert decisions[0]["symbol"] in ["ETH-USD", "BTC-USD"]

    def test_record_entry_and_exit(self, strategy):
        """Test recording trade entry and exit"""
        # Record entry
        trade_id = strategy.record_entry(
            entry_prices={"ETH-USD": 3000, "BTC-USD": 90000},
            llm_reasoning="Test entry",
            long_symbol="ETH-USD",
            short_symbol="BTC-USD"
        )

        assert strategy.has_active_trade()
        assert trade_id == 1

        # Record exit
        outcome = strategy.record_exit(
            trade_id=trade_id,
            exit_prices={"ETH-USD": 3100, "BTC-USD": 90500}
        )

        assert not strategy.has_active_trade()
        assert outcome is not None
        assert "correct_direction" in outcome

    def test_should_close_pair(self, strategy):
        """Test hold time checking"""
        # No active trade
        assert not strategy.should_close_pair()

        # Record entry
        strategy.record_entry(
            entry_prices={"ETH-USD": 3000, "BTC-USD": 90000},
            llm_reasoning="Test",
            long_symbol="ETH-USD",
            short_symbol="BTC-USD"
        )

        # Just opened, shouldn't close yet
        assert not strategy.should_close_pair()

        # Simulate time passing
        strategy._active_trade_open_time = datetime.now()
        from datetime import timedelta
        strategy._active_trade_open_time -= timedelta(seconds=3700)

        # Should close now
        assert strategy.should_close_pair()

    def test_sync_with_positions_both_legs(self, strategy):
        """Test syncing when both legs present"""
        positions = [
            {"symbol": "ETH-USD", "side": "LONG"},
            {"symbol": "BTC-USD", "side": "SHORT"}
        ]

        orphan = strategy.sync_with_positions(positions)

        assert orphan is None

    def test_sync_with_positions_orphan_detected(self, strategy):
        """Test syncing when one leg is missing"""
        positions = [
            {"symbol": "ETH-USD", "side": "LONG"}
            # BTC-USD missing
        ]

        orphan = strategy.sync_with_positions(positions)

        assert orphan == "ETH-USD"

    def test_get_status(self, strategy):
        """Test getting strategy status"""
        status = strategy.get_status()

        assert "strategy" in status
        assert status["strategy"] == "SELF_IMPROVING_PAIRS_V1"
        assert "performance" in status
        assert "bias" in status

    def test_full_trade_cycle(self, strategy):
        """Test a complete trade cycle with outcome tracking"""
        # 1. Open trade
        trade_id = strategy.record_entry(
            entry_prices={"ETH-USD": 3000, "BTC-USD": 90000},
            llm_reasoning="Initial trade",
            long_symbol="ETH-USD",
            short_symbol="BTC-USD"
        )

        # 2. Check status mid-trade
        assert strategy.has_active_trade()
        remaining = strategy.get_time_remaining()
        assert remaining is not None

        # 3. Close trade (ETH outperformed)
        outcome = strategy.record_exit(
            trade_id=trade_id,
            exit_prices={"ETH-USD": 3150, "BTC-USD": 90900}  # ETH +5%, BTC +1%
        )

        # 4. Verify outcome recorded correctly
        assert outcome["correct_direction"] == True
        assert not strategy.has_active_trade()

        # 5. Check stats updated
        stats = strategy.outcome_tracker.get_rolling_stats()
        assert stats["total"] == 1
        assert stats["correct"] == 1


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
