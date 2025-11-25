"""
Multi-Model Client
Supports DeepSeek and Qwen via direct APIs

Usage:
    client = MultiModelClient(
        deepseek_api_key="your_key",
        qwen_api_key="your_key",
        model="qwen-max"  # or "deepseek-chat"
    )
    response = client.query(prompt="Your trading prompt here")

Alpha Arena Winner: Qwen 3 MAX (+22.3% return, 43 trades in 17 days)
- Low frequency, high confidence trades
- Disciplined execution with strict stops
"""

import requests
import logging
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# Model configurations
MODEL_CONFIGS = {
    # DeepSeek models (direct API)
    "deepseek-chat": {
        "provider": "deepseek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model_id": "deepseek-chat",
        "input_cost_per_1k": 0.00014,
        "output_cost_per_1k": 0.00028,
    },
    "deepseek-reasoner": {
        "provider": "deepseek",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model_id": "deepseek-reasoner",
        "input_cost_per_1k": 0.00055,
        "output_cost_per_1k": 0.00220,
    },
    # Qwen models via OpenRouter - Alpha Arena winner!
    "qwen-max": {
        "provider": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model_id": "qwen/qwen3-235b-a22b",  # Qwen 3 235B = qwen-max equivalent
        "input_cost_per_1k": 0.0012,   # ~$1.20/M input
        "output_cost_per_1k": 0.006,   # ~$6.00/M output
    },
    "qwen-max-free": {
        "provider": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model_id": "qwen/qwen3-235b-a22b:free",  # FREE tier (rate limited)
        "input_cost_per_1k": 0.0,
        "output_cost_per_1k": 0.0,
    },
    "qwen-30b-free": {
        "provider": "openrouter",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "model_id": "qwen/qwen3-30b-a3b:free",  # FREE smaller model
        "input_cost_per_1k": 0.0,
        "output_cost_per_1k": 0.0,
    },
}


class MultiModelClient:
    """Multi-model API client supporting DeepSeek and Qwen (via OpenRouter)"""

    def __init__(
        self,
        deepseek_api_key: str = None,
        openrouter_api_key: str = None,
        model: str = "deepseek-chat",
        max_retries: int = 2,
        daily_spend_limit: float = 10.0,
        timeout: int = 60
    ):
        """
        Initialize multi-model client

        Args:
            deepseek_api_key: DeepSeek API key (for deepseek models)
            openrouter_api_key: OpenRouter API key (for Qwen models)
            model: Model name (default: deepseek-chat)
            max_retries: Number of retries on failure
            daily_spend_limit: Max USD to spend per day
            timeout: Request timeout in seconds
        """
        self.deepseek_api_key = deepseek_api_key
        self.openrouter_api_key = openrouter_api_key
        self.model = model
        self.max_retries = max_retries
        self.daily_spend_limit = daily_spend_limit
        self.timeout = timeout

        # Validate model
        if model not in MODEL_CONFIGS:
            available = ", ".join(MODEL_CONFIGS.keys())
            raise ValueError(f"Unknown model '{model}'. Available: {available}")

        self.config = MODEL_CONFIGS[model]
        self.provider = self.config["provider"]

        # Validate API key for provider
        if self.provider == "deepseek" and not deepseek_api_key:
            raise ValueError("DeepSeek API key required for DeepSeek models")
        if self.provider == "openrouter" and not openrouter_api_key:
            raise ValueError("OpenRouter API key required for Qwen models")

        # Track spending
        self._daily_spend = 0.0
        self._spend_reset_time = datetime.now() + timedelta(days=1)
        self._last_request_time = None
        self._min_request_interval = 1.0

        logger.info(f"✅ MultiModelClient initialized: {model} via {self.provider}")

    def switch_model(self, model: str):
        """Switch to a different model"""
        if model not in MODEL_CONFIGS:
            available = ", ".join(MODEL_CONFIGS.keys())
            raise ValueError(f"Unknown model '{model}'. Available: {available}")

        self.model = model
        self.config = MODEL_CONFIGS[model]
        self.provider = self.config["provider"]

        # Validate API key
        if self.provider == "deepseek" and not self.deepseek_api_key:
            raise ValueError("DeepSeek API key required for DeepSeek models")
        if self.provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError("OpenRouter API key required for Qwen models")

        logger.info(f"🔄 Switched to model: {model} via {self.provider}")

    def _get_api_key(self) -> str:
        """Get API key for current provider"""
        if self.provider == "deepseek":
            return self.deepseek_api_key
        elif self.provider == "openrouter":
            return self.openrouter_api_key
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _reset_daily_spend_if_needed(self):
        """Reset daily spend counter if new day"""
        if datetime.now() >= self._spend_reset_time:
            logger.info(f"Daily spend reset (previous: ${self._daily_spend:.4f})")
            self._daily_spend = 0.0
            self._spend_reset_time = datetime.now() + timedelta(days=1)

    def _check_spend_limit(self, estimated_cost: float):
        """Check if request would exceed daily spend limit"""
        self._reset_daily_spend_if_needed()

        if self._daily_spend + estimated_cost > self.daily_spend_limit:
            raise Exception(
                f"Daily spend limit exceeded: ${self._daily_spend:.4f} + ${estimated_cost:.4f} "
                f"> ${self.daily_spend_limit:.2f}"
            )

    def _rate_limit(self):
        """Enforce minimum time between requests"""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _calculate_cost(self, usage: Dict) -> float:
        """Calculate cost from token usage"""
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        input_cost = (prompt_tokens / 1000) * self.config["input_cost_per_1k"]
        output_cost = (completion_tokens / 1000) * self.config["output_cost_per_1k"]

        return input_cost + output_cost

    def query(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.1,
        retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Query the model with retry logic

        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature (0.1 for deterministic)
            retry_count: Current retry attempt

        Returns:
            Dict with keys: content, usage, cost, model
            None if all retries failed
        """
        # Estimate cost
        estimated_cost = ((len(prompt) / 4 + max_tokens) / 1000) * self.config["output_cost_per_1k"]
        self._check_spend_limit(estimated_cost)

        # Rate limiting
        self._rate_limit()

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json"
        }

        # Add OpenRouter-specific headers
        if self.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/trading-bot"
            headers["X-Title"] = "Trading Bot"

        payload = {
            "model": self.config["model_id"],
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            logger.info(f"{self.model} API request (attempt {retry_count + 1}/{self.max_retries + 1})...")

            response = requests.post(
                self.config["url"],
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})

                    # Calculate actual cost
                    cost = self._calculate_cost(usage)
                    self._daily_spend += cost

                    logger.info(
                        f"✅ {self.model} response received "
                        f"(tokens: {usage.get('total_tokens')}, cost: ${cost:.4f}, "
                        f"daily: ${self._daily_spend:.4f})"
                    )

                    return {
                        "content": content,
                        "usage": usage,
                        "cost": cost,
                        "model": self.model
                    }
                else:
                    logger.warning(f"{self.model} response missing 'choices'")
                    return None

            elif response.status_code == 429:
                wait_time = min(30 * (2 ** retry_count), 120)
                logger.warning(f"{self.model} rate limit (429), waiting {wait_time}s...")
                time.sleep(wait_time)

                if retry_count < self.max_retries:
                    return self.query(prompt, max_tokens, temperature, retry_count + 1)
                else:
                    logger.error("Max retries reached after rate limit")
                    return None

            elif response.status_code == 402:
                logger.error(f"{self.model} insufficient balance (402)")
                return None

            else:
                logger.error(f"{self.model} API error: HTTP {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")

                if retry_count < self.max_retries:
                    logger.info("Retrying in 2 seconds...")
                    time.sleep(2)
                    return self.query(prompt, max_tokens, temperature, retry_count + 1)
                else:
                    return None

        except requests.exceptions.Timeout:
            logger.error(f"{self.model} request timeout ({self.timeout}s)")

            if retry_count < self.max_retries:
                logger.info("Retrying...")
                return self.query(prompt, max_tokens, temperature, retry_count + 1)
            else:
                return None

        except Exception as e:
            logger.error(f"{self.model} API error: {e}")

            if retry_count < self.max_retries:
                logger.info("Retrying...")
                time.sleep(2)
                return self.query(prompt, max_tokens, temperature, retry_count + 1)
            else:
                return None

    def get_daily_spend(self) -> float:
        """Get current daily spend in USD"""
        self._reset_daily_spend_if_needed()
        return self._daily_spend

    def get_remaining_budget(self) -> float:
        """Get remaining budget for today"""
        self._reset_daily_spend_if_needed()
        return self.daily_spend_limit - self._daily_spend

    @staticmethod
    def list_models() -> Dict:
        """List all available models with their costs"""
        return {
            name: {
                "provider": cfg["provider"],
                "input_cost": f"${cfg['input_cost_per_1k']*1000:.2f}/M tokens",
                "output_cost": f"${cfg['output_cost_per_1k']*1000:.2f}/M tokens",
            }
            for name, cfg in MODEL_CONFIGS.items()
        }
