"""
DeepSeek Model Client
Handles API authentication, retries, and daily spend limits

Usage:
    client = ModelClient(api_key="your_key")
    response = client.query(prompt="Your trading prompt here")
"""

import requests
import logging
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ModelClient:
    """DeepSeek API client with authentication and retry logic"""

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        max_retries: int = 2,
        daily_spend_limit: float = 10.0,  # USD
        timeout: int = 30
    ):
        """
        Initialize DeepSeek model client

        Args:
            api_key: DeepSeek API key
            model: Model name (default: deepseek-chat)
            max_retries: Number of retries on failure (default: 2)
            daily_spend_limit: Max USD to spend per day (default: $10)
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.daily_spend_limit = daily_spend_limit
        self.timeout = timeout

        self.url = "https://api.deepseek.com/v1/chat/completions"

        # Track spending
        self._daily_spend = 0.0
        self._spend_reset_time = datetime.now() + timedelta(days=1)
        self._last_request_time = None

        # Rate limiting (minimal - run at full capacity)
        self._min_request_interval = 0.5  # Minimal delay for maximum throughput

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
        """
        Calculate cost from token usage

        DeepSeek pricing (as of 2025-01-30):
        - Input: $0.00014 per 1K tokens
        - Output: $0.00028 per 1K tokens
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        input_cost = (prompt_tokens / 1000) * 0.00014
        output_cost = (completion_tokens / 1000) * 0.00028

        return input_cost + output_cost

    def query(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.1,
        retry_count: int = 0
    ) -> Optional[Dict]:
        """
        Query DeepSeek API with retry logic

        Args:
            prompt: User prompt
            max_tokens: Max tokens to generate (default: 100)
            temperature: Sampling temperature (default: 0.1 for deterministic)
            retry_count: Current retry attempt (internal use)

        Returns:
            Dict with keys: content, usage, cost
            None if all retries failed
        """
        # Estimate cost (conservative: assume full token usage)
        estimated_cost = ((len(prompt) / 4 + max_tokens) / 1000) * 0.00028
        self._check_spend_limit(estimated_cost)

        # Rate limiting
        self._rate_limit()

        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
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
            logger.info(f"DeepSeek API request (attempt {retry_count + 1}/{self.max_retries + 1})...")

            response = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()

                # Extract response
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})

                    # Calculate actual cost
                    cost = self._calculate_cost(usage)
                    self._daily_spend += cost

                    logger.info(
                        f"✅ DeepSeek response received "
                        f"(tokens: {usage.get('total_tokens')}, cost: ${cost:.4f}, "
                        f"daily: ${self._daily_spend:.4f})"
                    )

                    return {
                        "content": content,
                        "usage": usage,
                        "cost": cost
                    }
                else:
                    logger.warning("DeepSeek response missing 'choices'")
                    return None

            elif response.status_code == 429:
                # Rate limited - use exponential backoff with longer delays
                # DeepSeek often needs 30-60 seconds to reset rate limits
                wait_time = min(30 * (2 ** retry_count), 120)  # 30s, 60s, 120s max
                logger.warning(f"DeepSeek rate limit (429), waiting {wait_time} seconds (exponential backoff)...")
                time.sleep(wait_time)

                if retry_count < self.max_retries:
                    return self.query(prompt, max_tokens, temperature, retry_count + 1)
                else:
                    logger.error("Max retries reached after rate limit")
                    return None

            elif response.status_code == 402:
                # Insufficient balance
                logger.error("DeepSeek insufficient balance (402)")
                return None

            else:
                logger.error(f"DeepSeek API error: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")

                if retry_count < self.max_retries:
                    logger.info(f"Retrying in 2 seconds...")
                    time.sleep(2)
                    return self.query(prompt, max_tokens, temperature, retry_count + 1)
                else:
                    return None

        except requests.exceptions.Timeout:
            logger.error(f"DeepSeek request timeout ({self.timeout}s)")

            if retry_count < self.max_retries:
                logger.info("Retrying...")
                return self.query(prompt, max_tokens, temperature, retry_count + 1)
            else:
                return None

        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")

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
        """Get remaining budget for today in USD"""
        self._reset_daily_spend_if_needed()
        return self.daily_spend_limit - self._daily_spend
