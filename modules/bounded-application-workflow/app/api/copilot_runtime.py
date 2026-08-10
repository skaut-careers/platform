from __future__ import annotations

from typing import Any, Optional, Union
from uuid import uuid4

from ag_ui.core import (
    EventType,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
)
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from ag_ui_langgraph.agent import PreparedStream
from copilotkit import LangGraphAGUIAgent
from fastapi import FastAPI
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from app.agents.orchestration.state import WorkflowGraphState
from app.domain.models import WorkflowInput
from app.agents.workflow_planning.plan import (
    DECISION,
    POLICY_APPLICATION,
    PROFILE_EXTRACTION,
    PROFILE_MATCHING,
    SIGNAL_EXTRACTION,
    WORKFLOW_PLANNING,
)

AGUI_WORKFLOW_AGENT_NAME = "application_workflow"
COPILOTKIT_PATH = "/copilotkit"

CANONICAL_WORKFLOW_NODES = frozenset(
    {
        PROFILE_EXTRACTION,
        WORKFLOW_PLANNING,
        SIGNAL_EXTRACTION,
        PROFILE_MATCHING,
        POLICY_APPLICATION,
        DECISION,
    }
)


class AguiWorkflowAgent(LangGraphAGUIAgent):
    """AG-UI adapter over the canonical graph. No chat ``messages`` in domain state."""

    def __init__(
        self,
        *,
        name: str,
        graph: CompiledStateGraph,
        description: Optional[str] = None,
        config: Union[Optional[RunnableConfig], dict] = None,
    ) -> None:
        super().__init__(
            name=name,
            graph=graph,
            description=description,
            config=config,
        )
        self.constant_schema_keys = ["tools", "copilotkit"]

    def clone(self) -> "AguiWorkflowAgent":
        return type(self)(
            name=self.name,
            graph=self.graph,
            description=self.description,
            config=dict(self.config) if self.config else None,
        )

    def _materialize_raw_state(self, input_data: RunAgentInput) -> RunAgentInput | None:
        """Product AG-UI entry: only raw texts; ``profile_extraction`` does the rest."""
        workflow_input = WorkflowInput.try_from_mapping(input_data.state or {})
        if workflow_input is None:
            return None

        thread_id = input_data.thread_id or str(uuid4())
        domain = WorkflowGraphState.from_workflow_input(
            workflow_input,
            workflow_id=thread_id,
        ).model_dump(mode="json")
        return input_data.model_copy(
            update={"thread_id": thread_id, "state": domain}
        )

    async def prepare_stream(
        self,
        input: RunAgentInput,
        agent_state: Any,
        config: RunnableConfig,
    ) -> PreparedStream:
        forwarded = input.forwarded_props or {}
        command = forwarded.get("command") or {}
        resuming = isinstance(command, dict) and command.get("resume") is not None

        if not resuming:
            materialized = self._materialize_raw_state(input)
            if materialized is None:
                thread_id = input.thread_id or str(uuid4())
                run_id = input.run_id
                return {
                    "stream": None,
                    "state": None,
                    "config": None,
                    "events_to_dispatch": [
                        RunStartedEvent(
                            type=EventType.RUN_STARTED,
                            thread_id=thread_id,
                            run_id=run_id,
                        ),
                        RunErrorEvent(
                            type=EventType.RUN_ERROR,
                            message=(
                                "profile_text and job_description_text are required"
                            ),
                        ),
                        RunFinishedEvent(
                            type=EventType.RUN_FINISHED,
                            thread_id=thread_id,
                            run_id=run_id,
                        ),
                    ],
                }
            input = materialized

        return await super().prepare_stream(input, agent_state, config)


def mount_copilotkit_runtime(
    app: FastAPI,
    *,
    graph: CompiledStateGraph,
) -> None:
    if not CANONICAL_WORKFLOW_NODES.issubset(set(graph.nodes)):
        missing = sorted(CANONICAL_WORKFLOW_NODES - set(graph.nodes))
        raise ValueError(
            "AG-UI must mount the canonical workflow graph; "
            f"missing nodes: {missing}"
        )

    add_langgraph_fastapi_endpoint(
        app,
        AguiWorkflowAgent(
            name=AGUI_WORKFLOW_AGENT_NAME,
            description=(
                "Run the bounded application workflow for a user profile "
                "and job description."
            ),
            graph=graph,
        ),
        path=COPILOTKIT_PATH,
    )


__all__ = [
    "AGUI_WORKFLOW_AGENT_NAME",
    "CANONICAL_WORKFLOW_NODES",
    "COPILOTKIT_PATH",
    "AguiWorkflowAgent",
    "WorkflowGraphState",
    "mount_copilotkit_runtime",
]
