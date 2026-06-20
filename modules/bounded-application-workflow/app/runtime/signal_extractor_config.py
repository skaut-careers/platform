from pydantic import Field

from app.runtime.config import RuntimeConfig


class SignalExtractorRuntimeConfig(RuntimeConfig):
    """Versioned runtime settings for LLM-backed signal extraction."""

    agent_name: str = Field(default="llm_signal_extractor", min_length=1)
    model: str = Field(default="gpt-5-mini", min_length=1)
    max_attempts: int = Field(default=2, ge=1, le=5)
