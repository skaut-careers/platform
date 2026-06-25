from app.agents.contracts import SignalExtractorInput, SignalExtractorOutput
from app.agents.signal_extraction.deterministic import extract_job_signals
from app.agents.signal_extraction.llm import LLMSignalExtractor

__all__ = ["DefaultSignalExtractor", "LLMSignalExtractor"]


class DefaultSignalExtractor:
    def run(self, agent_input: SignalExtractorInput) -> SignalExtractorOutput:
        signals = extract_job_signals(agent_input.job_description)
        return SignalExtractorOutput(signals=signals)
