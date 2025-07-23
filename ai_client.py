import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, TypeVar
import requests
from requests import HTTPError

T = TypeVar("T")


class AIClient(ABC):
    """Abstract base class for AI clients"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.model = config.get("model")

        # Require explicit temperature
        self.temperature = config.get("temperature")
        if self.temperature is None:
            raise ValueError("Temperature must be explicitly set in config.yaml")

        # Require explicit max_tokens
        self.max_tokens = config.get("max_tokens")
        if self.max_tokens is None:
            raise ValueError("Max tokens must be explicitly set in config.yaml")

    @abstractmethod
    def send_message(self, prompt: str, retry_attempts: int = 3) -> str:
        """Send message to AI and return response"""
        pass

    def _make_api_request(
        self,
        request_func: Callable[[], T],
        provider_name: str,
        retry_attempts: int = 3,
    ) -> T:
        """Common retry logic for provider API calls with exponential back-off."""
        for attempt in range(retry_attempts):
            try:
                return request_func()
            except Exception as e:
                if isinstance(e, HTTPError) and hasattr(e, 'response') and e.response is not None:
                    print(f"{provider_name} API error detail: {e.response.text}")
                if attempt < retry_attempts - 1:
                    print(f"{provider_name} API attempt {attempt + 1} failed: {e}")
                    time.sleep(2 ** attempt)
                else:
                    raise Exception(
                        f"{provider_name} API failed after {retry_attempts} attempts: {e}"
                    ) from e


class OpenAIClient(AIClient):
    """OpenAI API client implementation"""

    def send_message(self, prompt: str, retry_attempts: int = 3) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        def _request():
            # Build canonical OpenAI endpoint: ensure exactly one "/v1" segment
            base = self.base_url.rstrip("/")
            if not base.endswith("/v1"):
                base = f"{base}/v1"
            full_url = f"{base}/chat/completions"
            response = requests.post(full_url, headers=headers, json=data, timeout=120)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        return self._make_api_request(_request, "OpenAI", retry_attempts)


class AnthropicClient(AIClient):
    """Anthropic API client implementation"""

    def send_message(self, prompt: str, retry_attempts: int = 3) -> str:
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        def _request():
            response = requests.post(
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=data,
                timeout=120,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"]

        return self._make_api_request(_request, "Anthropic", retry_attempts)


class AIClientFactory:
    """Factory for creating AI clients"""

    @staticmethod
    def create_client(provider: str, config: Dict[str, Any]) -> AIClient:
        if provider == "openai":
            return OpenAIClient(config)
        elif provider == "anthropic":
            return AnthropicClient(config)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")