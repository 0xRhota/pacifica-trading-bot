"""
Prompt Strategy Configuration
Clean switching between prompt versions with easy rollback

Usage in bot:
    from llm_agent.config_prompts import get_prompt_formatter
    formatter = get_prompt_formatter()  # Returns active version
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION - Change this to switch strategies
# ============================================================================

# Options: "v1_original", "v2_deep_reasoning", "v7_alpha_arena", "v8_pure_pnl", "v9_qwen_enhanced"
# v8_pure_pnl: Pure PnL focus - low frequency, high conviction, let winners run
# v9_qwen_enhanced: Qwen's comprehensive scoring system with funding zones & OI confluence
ACTIVE_PROMPT_VERSION: Literal["v1_original", "v2_deep_reasoning", "v7_alpha_arena", "v8_pure_pnl", "v9_qwen_enhanced"] = "v9_qwen_enhanced"

# ============================================================================
# Strategy Descriptions
# ============================================================================

PROMPT_STRATEGIES = {
    "v1_original": {
        "description": "Original prompt with Deep42 macro context",
        "file": "llm_agent.llm.prompt_formatter",
        "class": "PromptFormatter",
        "features": [
            "Deep42 macro analysis (12h cache)",
            "General indicator references",
            "Brief explanation format",
            "24h volume context"
        ],
        "pros": [
            "Tested and stable",
            "Includes macro sentiment",
            "Fast decisions"
        ],
        "cons": [
            "Suggests invalid symbols (FOMO, RDNT)",
            "Vague reasoning ('likely oversold')",
            "Generic exits ('better opportunities')",
            "Mixes timeframes inappropriately"
        ]
    },
    "v2_deep_reasoning": {
        "description": "Enhanced prompt with mandatory exact citations and chain-of-thought",
        "file": "llm_agent.llm.prompt_formatter_v2_deep_reasoning",
        "class": "PromptFormatterV2",
        "features": [
            "NO Deep42 macro (5-min scalping focus)",
            "Chain-of-thought analysis structure",
            "Mandatory exact indicator citations",
            "Symbol validation enforcement",
            "Step-by-step reasoning process"
        ],
        "pros": [
            "Zero invalid symbol suggestions",
            "Precise indicator citations (no 'likely')",
            "Focused 5-min scalping strategy",
            "Higher quality reasoning",
            "Better timeframe alignment"
        ],
        "cons": [
            "Slightly longer prompts (more tokens)",
            "Untested in production",
            "May be slower if model analyzes deeply"
        ]
    },
    "v7_alpha_arena": {
        "description": "Alpha Arena winning formula - disciplined high-volume scalping",
        "file": "llm_agent.llm.prompt_formatter",
        "class": "PromptFormatter",
        "strategy_file": "llm_agent/prompts_archive/v7_alpha_arena_discipline.txt",
        "features": [
            "Based on Qwen +22.3% Alpha Arena win",
            "Mandatory stop-loss on every trade",
            "Strict invalidation conditions",
            "Signal → Execute → Exit (no hesitation)",
            "Structured output with exit plans",
            "Volume focus with profit discipline"
        ],
        "pros": [
            "Proven real-money performance",
            "Strict risk discipline",
            "Clear invalidation rules",
            "Works with any model (DeepSeek, Qwen)",
            "High volume + controlled risk"
        ],
        "cons": [
            "May exit too early on runners",
            "Strict rules may miss some opportunities",
            "Requires discipline from model"
        ]
    },
    "v8_pure_pnl": {
        "description": "Pure PnL maximization - low frequency, high conviction, asymmetric R:R",
        "file": "llm_agent.llm.prompt_formatter",
        "class": "PromptFormatter",
        "strategy_file": "llm_agent/prompts_archive/v8_alpha_arena_pure_pnl.txt",
        "features": [
            "Exact Alpha Arena winning formula",
            "LOW frequency (quality > quantity)",
            "Asymmetric R:R (risk 1% to make 2-4%)",
            "Let winners run (+2-4% targets)",
            "NO_TRADE when no edge exists",
            "Only 3+ confluent signals = entry"
        ],
        "pros": [
            "Maximizes raw PnL",
            "Ignores volume/trade count",
            "Proven +22% in 17 days formula",
            "Patience enforced (waits for setup)",
            "Better for low-points environments"
        ],
        "cons": [
            "Very low trade frequency",
            "May sit idle for hours",
            "Requires model discipline"
        ]
    },
    "v9_qwen_enhanced": {
        "description": "Qwen-enhanced scoring system with funding zones, OI confluence, NO Deep42",
        "file": "llm_agent.llm.prompt_formatter",
        "class": "PromptFormatter",
        "strategy_file": "llm_agent/prompts_archive/v9_qwen_enhanced.txt",
        "features": [
            "5-signal scoring system (RSI, MACD, Volume, Price Action, OI)",
            "Score threshold: 3.0+ to trade",
            "5 funding rate zones (contrarian signals)",
            "OI + price confluence for entry confirmation",
            "NO Deep42 macro context (removes long-only bias)",
            "Detailed scoring breakdown in response",
            "Asymmetric R:R (2:1 to 4:1 minimum)"
        ],
        "pros": [
            "Quantitative signal scoring (3.0+ required)",
            "Funding rates as contrarian indicators",
            "OI confluence prevents fake moves",
            "No Deep42 bias",
            "Clear NO_TRADE criteria with scores"
        ],
        "cons": [
            "More complex scoring may slow model",
            "Requires good OI data availability",
            "Untested in production"
        ]
    }
}

# ============================================================================
# Functions
# ============================================================================

def get_prompt_formatter():
    """
    Get the active prompt formatter instance

    Returns:
        PromptFormatter or PromptFormatterV2 instance based on ACTIVE_PROMPT_VERSION

    Example:
        formatter = get_prompt_formatter()
        prompt = formatter.format_trading_prompt(...)
    """
    strategy = PROMPT_STRATEGIES[ACTIVE_PROMPT_VERSION]

    logger.info("=" * 80)
    logger.info(f"🎯 ACTIVE PROMPT STRATEGY: {ACTIVE_PROMPT_VERSION}")
    logger.info(f"📋 Description: {strategy['description']}")
    logger.info(f"✨ Features:")
    for feature in strategy['features']:
        logger.info(f"   - {feature}")
    logger.info("=" * 80)

    # Dynamic import based on config
    module_path = strategy['file']
    class_name = strategy['class']

    # Import the module
    import importlib
    import os
    module = importlib.import_module(module_path)

    # Get the class
    formatter_class = getattr(module, class_name)

    # Check if strategy has a file to load
    strategy_file = strategy.get('strategy_file')
    if strategy_file:
        # Resolve relative path from project root
        if not os.path.isabs(strategy_file):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            strategy_file = os.path.join(project_root, strategy_file)

        logger.info(f"📂 Loading strategy file: {strategy_file}")
        return formatter_class(strategy_file=strategy_file)

    # Return instance without strategy file
    return formatter_class()


def get_active_strategy_info() -> dict:
    """
    Get information about the currently active prompt strategy

    Returns:
        Dict with strategy details (description, features, pros, cons)
    """
    return {
        "version": ACTIVE_PROMPT_VERSION,
        **PROMPT_STRATEGIES[ACTIVE_PROMPT_VERSION]
    }


def list_available_strategies() -> dict:
    """
    List all available prompt strategies

    Returns:
        Dict mapping version names to strategy details
    """
    return PROMPT_STRATEGIES


# ============================================================================
# Quick Reference
# ============================================================================
"""
QUICK ROLLBACK GUIDE:

1. TO TEST V2:
   - Change ACTIVE_PROMPT_VERSION = "v2_deep_reasoning"
   - Restart bot
   - Monitor logs for "[V2 PROMPT]" markers
   - Compare reasoning quality

2. TO ROLLBACK TO V1:
   - Change ACTIVE_PROMPT_VERSION = "v1_original"
   - Restart bot
   - Everything returns to previous behavior

3. NO CODE CHANGES NEEDED:
   - Bot automatically uses get_prompt_formatter()
   - Just change the config variable above
   - Clean separation of concerns

EXPECTED IMPROVEMENTS WITH V2:
- Invalid symbols: ~3 per cycle → 0 per cycle
- Indicator specificity: ~40% → ~85%
- Reasoning quality: Grade C+ → Grade B+
- Deep42 noise: Removed entirely

ROLLBACK IF:
- Decisions take >15 seconds (too slow)
- Reasoning becomes TOO verbose
- Cost increases >2x
- Any unexpected errors
"""
