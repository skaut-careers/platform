from app.domain.job_signals import JobSignals, SignalCategory


def test_job_signals_supports_all_signal_categories():
    signals = JobSignals(
        required_skills=["Python", "LLMs"],
        preferred_skills=["FastAPI", "Evaluation"],
        seniority_signals=["mid-senior", "team lead expectations"],
        production_expectations=["large-scale inference", "on-call rotation"],
        risk_indicators=["ambiguous scope", "high infrastructure ownership"],
        missing_signals=["salary range", "team size"],
    )

    assert signals.required_skills == ["Python", "LLMs"]
    assert signals.preferred_skills == ["FastAPI", "Evaluation"]
    assert signals.seniority_signals == ["mid-senior", "team lead expectations"]
    assert signals.production_expectations == [
        "large-scale inference",
        "on-call rotation",
    ]
    assert signals.risk_indicators == [
        "ambiguous scope",
        "high infrastructure ownership",
    ]
    assert signals.missing_signals == ["salary range", "team size"]


def test_job_signals_defaults_to_empty_lists():
    signals = JobSignals()

    assert signals.required_skills == []
    assert signals.preferred_skills == []
    assert signals.seniority_signals == []
    assert signals.production_expectations == []
    assert signals.risk_indicators == []
    assert signals.missing_signals == []


def test_signal_category_covers_job_signals_fields():
    categories = {category.value for category in SignalCategory}

    assert categories == {
        "required_skills",
        "preferred_skills",
        "seniority_signals",
        "production_expectations",
        "risk_indicators",
        "missing_signals",
    }
