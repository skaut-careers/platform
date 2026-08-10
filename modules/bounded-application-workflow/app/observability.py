from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

import logfire

from app.runtime.config_loader import local_env

if TYPE_CHECKING:
    from fastapi import FastAPI

# LangSmith OTel → Logfire for LangGraph node/step spans. Must run before langgraph import.
os.environ.setdefault("LANGSMITH_OTEL_ENABLED", "true")
os.environ.setdefault("LANGSMITH_OTEL_ONLY", "true")
os.environ.setdefault("LANGSMITH_TRACING", "true")

_SERVICE_NAME = "bounded-application-workflow"
_configured = False
_libraries_instrumented = False


def _under_pytest() -> bool:
    return "pytest" in sys.modules or bool(os.environ.get("PYTEST_CURRENT_TEST"))


def configure_observability(*, force: bool = False) -> None:
    """Configure Logfire. Safe to call multiple times; no-ops after the first."""
    global _configured
    if _configured and not force:
        return

    token = local_env().get("LOGFIRE_TOKEN") or None
    logfire.configure(
        token=token,
        send_to_logfire="if-token-present",
        service_name=_SERVICE_NAME,
        console=False if _under_pytest() else None,
    )
    _configured = True


def instrument_libraries() -> None:
    """Instrument Pydantic AI (and HTTPX) once per process."""
    global _libraries_instrumented
    configure_observability()
    if _libraries_instrumented:
        return

    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx()
    _libraries_instrumented = True


def instrument_app(app: FastAPI) -> None:
    """Configure Logfire and instrument the FastAPI app + agent stack."""
    instrument_libraries()
    logfire.instrument_fastapi(app)
