"""
Deep42 Query Tool
Allows LLM to query Deep42/Cambrian directly with custom questions
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class Deep42Tool:
    """Tool for LLM to query Deep42 with custom questions"""

    def __init__(self, cambrian_api_key: str):
        self.cambrian_api_key = cambrian_api_key
        self.base_url = "https://deep42.cambrian.network/api/v1/deep42/agents/deep42"

    def query(self, question: str) -> Optional[str]:
        """
        Query Deep42 with a custom question

        Args:
            question: The question to ask Deep42

        Returns:
            Deep42's answer as a string, or None if failed
        """
        try:
            headers = {
                "X-API-KEY": self.cambrian_api_key,
                "Content-Type": "application/json"
            }
            params = {"question": question}

            response = requests.get(self.base_url, headers=headers, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer")
                logger.info(f"✅ Deep42 query successful: {question[:50]}...")
                return answer
            else:
                logger.warning(f"Deep42 query failed: HTTP {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Deep42 query error: {e}")
            return None
