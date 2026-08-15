from app.agents.contracts import JobSignalExtractorInput, JobSignalExtractorOutput
from app.agents.job_signal_extraction.deterministic import extract_job_signals
from app.agents.job_signal_extraction.llm import LLMJobSignalExtractor

__all__ = ["DefaultJobSignalExtractor", "LLMJobSignalExtractor"]


class DefaultJobSignalExtractor:
    def run(self, agent_input: JobSignalExtractorInput) -> JobSignalExtractorOutput:
        job_signals = extract_job_signals(agent_input.job_description_text)
        return JobSignalExtractorOutput(job_signals=job_signals)
