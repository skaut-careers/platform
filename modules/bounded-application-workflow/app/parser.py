from app.domain.models import JobDescription


def parse_job_description(raw_text: str) -> JobDescription:
    if not raw_text.strip():
        raise ValueError("Job description text cannot be empty.")

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    title = lines[0]

    company = None
    location = None
    seniority = None
    employment_type = None

    for line in lines:
        lower = line.lower()

        if lower.startswith("company:"):
            company = line.split(":", 1)[1].strip()

        elif lower.startswith("location:"):
            location = line.split(":", 1)[1].strip()

        elif lower.startswith("seniority:"):
            seniority = line.split(":", 1)[1].strip()

        elif lower.startswith("employment type:"):
            employment_type = line.split(":", 1)[1].strip()

    return JobDescription(
        title=title,
        company=company,
        location=location,
        description=raw_text,
        seniority=seniority,
        employment_type=employment_type,
    )