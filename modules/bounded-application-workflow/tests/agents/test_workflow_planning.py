from app.agents.workflow_planning.plan import (
    WorkflowPlan,
    compare_plan,
    default_workflow_plan,
)


def test_default_workflow_plan():
    stages = default_workflow_plan().stages
    assert stages[0] == "profile_extraction"
    assert stages[-1] == "decision"
    assert "signal_extraction" in stages
    assert stages.index("signal_extraction") < stages.index("workflow_planning")
    assert "human_review" not in stages


def test_compare_plan_flags_skipped_stage():
    base = default_workflow_plan().stages
    plan = WorkflowPlan(stages=[*base[:-1], "extra_stage", base[-1]])
    report = compare_plan(plan, base)
    assert report.followed_plan is False
    assert report.skipped_stages == ["extra_stage"]


def test_compare_plan_followed():
    plan = default_workflow_plan()
    report = compare_plan(plan, list(plan.stages))
    assert report.followed_plan is True
    assert not report.skipped_stages and not report.unplanned_stages
