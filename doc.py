import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore


class AIProvider:
    """Utility class to call different LLM providers with a unified interface."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _call_openai(self, base_url: str, model: str, system_msg: str, user_msg: str) -> str:
        if OpenAI is None:
            raise RuntimeError("OpenAI library is not available")
        client = OpenAI(api_key=self.api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=1,
            max_tokens=4000,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, model: str, system_msg: str, user_msg: str) -> str:
        if anthropic is None:
            raise RuntimeError("anthropic library is not available")
        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            temperature=1,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )
        # Anthropic responses return a list of message parts
        return "".join(part.text for part in msg.content)

    def query(self, provider: str, system_msg: str, user_msg: str) -> Dict[str, Any]:
        """Call the selected provider and return the parsed JSON response."""
        if provider == "deepseek":
            content = self._call_openai(
                base_url="https://api.deepseek.com",
                model="deepseek-chat",
                system_msg=system_msg,
                user_msg=user_msg,
            )
        elif provider == "openai":
            content = self._call_openai(
                base_url="",
                model="gpt-4o-mini",
                system_msg=system_msg,
                user_msg=user_msg,
            )
        elif provider == "anthropic":
            content = self._call_anthropic(
                model="claude-opus-4-20250514",
                system_msg=system_msg,
                user_msg=user_msg,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON response from {provider}: {exc}") from exc


def call_llm(provider: str, system_message: str, user_message: str, api_key: str) -> Dict[str, Any]:
    """Public helper to query an LLM and return JSON."""
    client = AIProvider(api_key)
    return client.query(provider, system_message, user_message)


@dataclass
class Item:
    """Simple container for scraped content."""
    url: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


def validate_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder validation that returns the input unchanged."""
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be a dictionary")
    return analysis


def process_item(validated_item: Item, system_message: str, user_message: str,
                 provider: str, api_key: str) -> Dict[str, Any]:
    """Run an item through the selected LLM and return processed structure."""
    llm_result = call_llm(provider, system_message, user_message, api_key)
    if "analyses" in llm_result and llm_result["analyses"]:
        analysis = llm_result["analyses"][0]
        validated = validate_analysis(analysis)
        analysis_json = json.dumps(validated, ensure_ascii=False)
        return {
            "url": validated_item.url,
            "content": validated_item.content,
            "ai_processed_content": analysis_json,
            "metadata": {"original_metadata": validated_item.metadata or {}}
        }
    raise ValueError("LLM result missing 'analyses' field")
