import json
import os
from typing import Any, Protocol, runtime_checkable


class LLMClientError(RuntimeError):
    """Raised when an LLM provider returns an unusable response."""


@runtime_checkable
class LLMClient(Protocol):
    """Minimal client surface for structured JSON completions."""

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]: ...


class OpenAILLMClient:
    """OpenAI Responses API client with JSON-schema structured output."""

    def __init__(
        self,
        *,
        model: str = "gpt-5-mini",
        api_key: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._api_key:
            raise LLMClientError("OPENAI_API_KEY is not configured")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMClientError(
                "openai package is required for OpenAILLMClient"
            ) from exc

        client = OpenAI(api_key=self._api_key)
        try:
            response = client.responses.create(
                model=self._model,
                instructions=system,
                input=user,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": response_schema.get("title", "structured_output"),
                        "strict": True,
                        "schema": response_schema,
                    }
                },
            )
        except Exception as exc:
            raise LLMClientError(f"OpenAI request failed: {exc}") from exc

        if getattr(response, "status", None) == "failed":
            raise LLMClientError("OpenAI response failed")

        content = response.output_text
        if not content:
            raise LLMClientError("OpenAI returned an empty completion")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMClientError("OpenAI returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise LLMClientError("OpenAI JSON payload must be an object")

        return payload
