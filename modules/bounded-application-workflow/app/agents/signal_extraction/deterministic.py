from app.domain.models import JobSignals
from app.domain.text_processing import (
    experience_requirements_from_job,
    missing_signals_from_job,
    normalize_job_signals,
    places_from_text,
    risk_indicators_from_job,
    seniority_signals_from_job,
    skills_from_job_text,
    work_arrangements_from_text,
)


def extract_job_signals(job_text: str) -> JobSignals:
    required_skills, preferred_skills = skills_from_job_text(job_text)
    work_arrangements = work_arrangements_from_text(job_text)

    return normalize_job_signals(
        JobSignals(
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            seniority_signals=seniority_signals_from_job(job_text),
            experience_requirements=experience_requirements_from_job(job_text),
            work_arrangements=work_arrangements,
            location_signals=places_from_text(job_text),
            risk_indicators=risk_indicators_from_job(job_text),
            missing_signals=missing_signals_from_job(
                job_text, work_arrangements=work_arrangements
            ),
        )
    )
