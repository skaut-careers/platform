import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.llm.client import LLMClientError, OpenAILLMClient

_SCHEMA = {"title": "JobSignals", "type": "object", "additionalProperties": False}
_CALL = {"system": "sys", "user": "user", "response_schema": _SCHEMA}


def test_complete_json_uses_responses_api():
    payload = {"required_skills": ["Python"]}
    create = MagicMock(
        return_value=SimpleNamespace(status="completed", output_text=json.dumps(payload))
    )
    with patch(
        "openai.OpenAI",
        return_value=SimpleNamespace(responses=SimpleNamespace(create=create)),
    ):
        assert OpenAILLMClient(api_key="k").complete_json(**_CALL) == payload

    kwargs = create.call_args.kwargs
    assert kwargs["model"] == "gpt-5-mini"
    assert kwargs["text"]["format"]["type"] == "json_schema"


def test_complete_json_requires_api_key():
    with pytest.raises(LLMClientError, match="OPENAI_API_KEY"):
        OpenAILLMClient(api_key=None).complete_json(**_CALL)


def test_complete_json_wraps_provider_errors():
    def create(**_: object) -> None:
        raise RuntimeError("offline")

    with patch(
        "openai.OpenAI",
        return_value=SimpleNamespace(responses=SimpleNamespace(create=create)),
    ):
        with pytest.raises(LLMClientError, match="OpenAI request failed"):
            OpenAILLMClient(api_key="k").complete_json(**_CALL)
