from __future__ import annotations

import asyncio
import uuid

import pytest
from ag_ui.core import EventType, RunAgentInput
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langgraph.graph import END, START, StateGraph

from app.agents.orchestration.state import WorkflowGraphState
from app.agents.orchestration.stages import CANONICAL_STAGES
from app.agents.wiring import create_agents
from app.api.copilot_runtime import (
    AGUI_WORKFLOW_AGENT_NAME,
    CANONICAL_WORKFLOW_NODES,
    AguiWorkflowAgent,
    mount_copilotkit_runtime,
)
from app.api.main import create_app
from app.domain.models import WorkflowOutput
from tests.conftest import expected_decision, runtime_config, workflow_input

_CORE_NODES = frozenset(CANONICAL_STAGES)


def _orchestrator():
    return create_agents(runtime_config=runtime_config(version="v1"))


def _initial_state(*, thread_id: str | None = None) -> WorkflowGraphState:
    return WorkflowGraphState.from_workflow_input(
        workflow_input("strong_match.json"),
        workflow_id=thread_id,
    )


def _raw_state(fixture_name: str = "strong_match.json") -> dict:
    wi = workflow_input(fixture_name)
    return {
        "profile_text": wi.profile_text,
        "job_description_text": wi.job_description_text,
    }


def _run_input(state: dict) -> RunAgentInput:
    return RunAgentInput(
        thread_id=str(uuid.uuid4()),
        run_id=str(uuid.uuid4()),
        messages=[],
        state=state,
        tools=[],
        context=[],
        forwarded_props={},
    )


def _run_agui(state: dict):
    agent = AguiWorkflowAgent(
        name=AGUI_WORKFLOW_AGENT_NAME, graph=_orchestrator().graph
    )

    async def _events():
        return [event async for event in agent.run(_run_input(state))]

    return asyncio.run(_events())


def test_agui_agent_exposes_canonical_graph():
    orchestrator = _orchestrator()
    agent = AguiWorkflowAgent(name=AGUI_WORKFLOW_AGENT_NAME, graph=orchestrator.graph)
    assert agent.graph is orchestrator.graph
    assert CANONICAL_WORKFLOW_NODES.issubset(set(agent.graph.nodes))


def test_canonical_graph_runs_core_nodes():
    orchestrator = _orchestrator()
    thread_id = str(uuid.uuid4())
    seen: list[str] = []

    async def _collect() -> None:
        async for event in orchestrator.graph.astream_events(
            _initial_state(thread_id=thread_id),
            {"configurable": {"thread_id": thread_id}},
            version="v2",
        ):
            if event.get("event") != "on_chain_end":
                continue
            node = (event.get("metadata") or {}).get("langgraph_node")
            if node:
                seen.append(node)

    asyncio.run(_collect())
    assert _CORE_NODES.issubset(seen)
    assert (
        orchestrator.graph.get_state({"configurable": {"thread_id": thread_id}}).values.get(
            "output"
        )
        is not None
    )


def test_checkpoint_state_isolated_by_thread_id():
    orchestrator = _orchestrator()
    thread_a, thread_b = str(uuid.uuid4()), str(uuid.uuid4())

    async def _run(thread_id: str) -> None:
        await orchestrator.graph.ainvoke(
            _initial_state(thread_id=thread_id),
            {"configurable": {"thread_id": thread_id}},
        )

    asyncio.run(_run(thread_a))
    asyncio.run(_run(thread_b))

    id_a = orchestrator.graph.get_state(
        {"configurable": {"thread_id": thread_a}}
    ).values["workflow_id"]
    id_b = orchestrator.graph.get_state(
        {"configurable": {"thread_id": thread_b}}
    ).values["workflow_id"]
    assert id_a == thread_a
    assert id_b == thread_b


def test_agui_agent_run_emits_canonical_step_nodes():
    events = _run_agui(_raw_state())
    steps = {
        event.step_name
        for event in events
        if event.type == EventType.STEP_STARTED and event.step_name
    }
    assert _CORE_NODES.issubset(steps)


def test_agui_agent_run_returns_renderable_decision():
    fixture = "strong_match.json"
    events = _run_agui(_raw_state(fixture))
    assert not any(event.type == EventType.RUN_ERROR for event in events)
    assert any(event.type == EventType.RUN_FINISHED for event in events)

    output = next(
        (
            event.snapshot.get("output")
            for event in reversed(events)
            if event.type == EventType.STATE_SNAPSHOT
            and isinstance(event.snapshot, dict)
            and event.snapshot.get("output") is not None
        ),
        None,
    )
    assert isinstance(output, WorkflowOutput)
    decision = output.decision
    assert decision.decision == expected_decision(fixture)
    assert isinstance(decision.score, (int, float))
    assert isinstance(decision.reasons, list)
    assert isinstance(decision.risks, list)


def test_agui_agent_rejects_empty_or_invalid_state():
    for state in ({}, {"profile_text": "cv", "job_description_text": "   "}):
        message = next(
            (
                event.message
                for event in _run_agui(state)
                if event.type == EventType.RUN_ERROR
            ),
            None,
        )
        assert message is not None
        assert "profile_text and job_description_text are required" in message


def test_app_mounts_orchestrator_canonical_graph():
    orchestrator = _orchestrator()
    client = TestClient(create_app(orchestrator=orchestrator))
    assert client.get("/copilotkit/health").json()["agent"]["name"] == (
        AGUI_WORKFLOW_AGENT_NAME
    )
    assert CANONICAL_WORKFLOW_NODES.issubset(set(orchestrator.graph.nodes))
