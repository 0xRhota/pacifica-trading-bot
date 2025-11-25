#!/usr/bin/env python3
"""
QA Check Script
Validates all Phase 1-3 code before going live

Checks:
1. All imports work
2. All classes can be instantiated
3. Basic functionality tests
4. Integration tests (dry-run)
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_imports():
    """Check all module imports"""
    logger.info("=" * 80)
    logger.info("QA CHECK 1: Module Imports")
    logger.info("=" * 80)

    try:
        # Phase 1: Data modules
        from llm_agent.data import (
            OIDataFetcher,
            MacroContextFetcher,
            PacificaDataFetcher,
            IndicatorCalculator,
            MarketDataAggregator
        )
        logger.info("✅ Phase 1 data modules imported")

        # Phase 2: LLM modules
        from llm_agent.llm import (
            ModelClient,
            PromptFormatter,
            ResponseParser,
            LLMTradingAgent
        )
        logger.info("✅ Phase 2 LLM modules imported")

        # Phase 3: Execution modules
        from llm_agent.execution import TradeExecutor
        logger.info("✅ Phase 3 execution modules imported")

        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def check_phase1_instantiation():
    """Check Phase 1 classes can be instantiated"""
    logger.info("\n" + "=" * 80)
    logger.info("QA CHECK 2: Phase 1 Instantiation")
    logger.info("=" * 80)

    try:
        from llm_agent.data import (
            OIDataFetcher,
            MacroContextFetcher,
            PacificaDataFetcher,
            IndicatorCalculator,
            MarketDataAggregator
        )

        # Test instantiation
        oi_fetcher = OIDataFetcher()
        logger.info("✅ OIDataFetcher instantiated")

        macro_fetcher = MacroContextFetcher(
            cambrian_api_key="test_key",
            refresh_interval_hours=12
        )
        logger.info("✅ MacroContextFetcher instantiated")

        pacifica_fetcher = PacificaDataFetcher()
        logger.info("✅ PacificaDataFetcher instantiated")

        indicator_calc = IndicatorCalculator()
        logger.info("✅ IndicatorCalculator instantiated")

        aggregator = MarketDataAggregator(
            cambrian_api_key="test_key",
            interval="15m",
            candle_limit=100
        )
        logger.info("✅ MarketDataAggregator instantiated")

        return True

    except Exception as e:
        logger.error(f"❌ Phase 1 instantiation failed: {e}")
        return False


def check_phase2_instantiation():
    """Check Phase 2 classes can be instantiated"""
    logger.info("\n" + "=" * 80)
    logger.info("QA CHECK 3: Phase 2 Instantiation")
    logger.info("=" * 80)

    try:
        from llm_agent.llm import (
            ModelClient,
            PromptFormatter,
            ResponseParser,
            LLMTradingAgent
        )

        # Test instantiation
        model_client = ModelClient(
            api_key="test_key",
            model="deepseek-chat"
        )
        logger.info("✅ ModelClient instantiated")

        prompt_formatter = PromptFormatter()
        logger.info("✅ PromptFormatter instantiated")

        response_parser = ResponseParser()
        logger.info("✅ ResponseParser instantiated")

        llm_agent = LLMTradingAgent(
            deepseek_api_key="test_key",
            model="deepseek-chat"
        )
        logger.info("✅ LLMTradingAgent instantiated")

        return True

    except Exception as e:
        logger.error(f"❌ Phase 2 instantiation failed: {e}")
        return False


def check_response_parser():
    """Check ResponseParser with test cases"""
    logger.info("\n" + "=" * 80)
    logger.info("QA CHECK 4: Response Parser Validation")
    logger.info("=" * 80)

    try:
        from llm_agent.llm import ResponseParser

        parser = ResponseParser()

        # Test case 1: BUY
        response1 = "DECISION: BUY SOL\nREASON: Strong momentum and bullish indicators"
        parsed1 = parser.parse_response(response1)
        assert parsed1 is not None, "Failed to parse BUY response"
        assert parsed1['action'] == "BUY", f"Wrong action: {parsed1['action']}"
        assert parsed1['symbol'] == "SOL", f"Wrong symbol: {parsed1['symbol']}"
        logger.info("✅ BUY response parsed correctly")

        # Test case 2: SELL
        response2 = "DECISION: SELL ETH\nREASON: Bearish reversal pattern detected"
        parsed2 = parser.parse_response(response2)
        assert parsed2 is not None, "Failed to parse SELL response"
        assert parsed2['action'] == "SELL", f"Wrong action: {parsed2['action']}"
        assert parsed2['symbol'] == "ETH", f"Wrong symbol: {parsed2['symbol']}"
        logger.info("✅ SELL response parsed correctly")

        # Test case 3: CLOSE
        response3 = "DECISION: CLOSE BTC\nREASON: Taking profits at resistance"
        parsed3 = parser.parse_response(response3)
        assert parsed3 is not None, "Failed to parse CLOSE response"
        assert parsed3['action'] == "CLOSE", f"Wrong action: {parsed3['action']}"
        assert parsed3['symbol'] == "BTC", f"Wrong symbol: {parsed3['symbol']}"
        logger.info("✅ CLOSE response parsed correctly")

        # Test case 4: NOTHING
        response4 = "DECISION: NOTHING\nREASON: Waiting for clearer signals"
        parsed4 = parser.parse_response(response4)
        assert parsed4 is not None, "Failed to parse NOTHING response"
        assert parsed4['action'] == "NOTHING", f"Wrong action: {parsed4['action']}"
        assert parsed4['symbol'] is None, f"Symbol should be None: {parsed4['symbol']}"
        logger.info("✅ NOTHING response parsed correctly")

        # Test case 5: Invalid symbol
        response5 = "DECISION: BUY INVALID\nREASON: Test"
        parsed5 = parser.parse_response(response5)
        assert parsed5 is None, "Should reject invalid symbol"
        logger.info("✅ Invalid symbol rejected correctly")

        return True

    except AssertionError as e:
        logger.error(f"❌ Response parser test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Response parser error: {e}")
        return False


def check_prompt_formatter():
    """Check PromptFormatter output"""
    logger.info("\n" + "=" * 80)
    logger.info("QA CHECK 5: Prompt Formatter")
    logger.info("=" * 80)

    try:
        from llm_agent.llm import PromptFormatter

        formatter = PromptFormatter()

        # Test formatting
        macro = "Test macro context"
        market_table = "Symbol  Price\nSOL     $200"
        positions = []

        prompt = formatter.format_trading_prompt(macro, market_table, positions)

        assert "Test macro context" in prompt, "Macro context missing"
        assert "SOL" in prompt, "Market table missing"
        assert "Open Positions: None" in prompt, "Positions section missing"
        assert "DECISION:" in prompt, "Instructions missing"
        assert "BUY" in prompt and "SELL" in prompt and "CLOSE" in prompt, "Actions missing"
        assert "FULL FREEDOM" in prompt, "Freedom clause missing"

        logger.info("✅ Prompt formatted correctly")
        logger.info(f"   Prompt length: {len(prompt)} characters")

        return True

    except AssertionError as e:
        logger.error(f"❌ Prompt formatter test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Prompt formatter error: {e}")
        return False


def main():
    """Run all QA checks"""

    logger.info("\n")
    logger.info("*" * 80)
    logger.info("LLM TRADING BOT - QA CHECK SUITE")
    logger.info("*" * 80)
    logger.info("\n")

    results = []

    # Run checks
    results.append(("Module Imports", check_imports()))
    results.append(("Phase 1 Instantiation", check_phase1_instantiation()))
    results.append(("Phase 2 Instantiation", check_phase2_instantiation()))
    results.append(("Response Parser", check_response_parser()))
    results.append(("Prompt Formatter", check_prompt_formatter()))

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("QA CHECK SUMMARY")
    logger.info("=" * 80)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{name:<30} {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 80)

    if all_passed:
        logger.info("\n✅ ALL QA CHECKS PASSED - Ready for testing")
        return 0
    else:
        logger.info("\n❌ SOME QA CHECKS FAILED - Fix issues before testing")
        return 1


if __name__ == "__main__":
    sys.exit(main())
