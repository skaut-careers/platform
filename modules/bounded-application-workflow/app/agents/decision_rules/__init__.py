from app.agents.contracts import DecisionPolicyInput, DecisionPolicyOutput
from app.agents.decision_rules.rules import build_workflow_decision

__all__ = ["DefaultDecisionPolicy"]


class DefaultDecisionPolicy:
    def run(self, agent_input: DecisionPolicyInput) -> DecisionPolicyOutput:
        decision = build_workflow_decision(agent_input.match, agent_input.signals)
        return DecisionPolicyOutput(decision=decision)
