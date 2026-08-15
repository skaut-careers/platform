from app.agents.contracts import (
    MatchDeciderInput,
    MatchDeciderOutput,
)
from app.agents.match_decision.deterministic import (
    match_and_decide,
)
from app.agents.match_decision.llm import LLMMatchDecider

__all__ = ["DefaultMatchDecider", "LLMMatchDecider"]


class DefaultMatchDecider:
    def run(
        self, agent_input: MatchDeciderInput
    ) -> MatchDeciderOutput:
        return MatchDeciderOutput(
            result=match_and_decide(
                agent_input.user_profile,
                agent_input.job_signals,
            )
        )
