"""Read verified-source questions and candidate repeats from saved analysis."""

from agents.analysis import get_analysis


def passages_for_topic(topic: str, subject: str, limit: int = 8) -> list[dict]:
    result = get_analysis(subject)
    if not result:
        return []
    return [
        {"year": q["year"], "filename": q["filename"], "page": q["page"],
         "text": q["question"]}
        for q in result["questions"] if q.get("topic") == topic
    ][:limit]


def recurring_questions(subject: str, min_years: int = 2) -> list[dict]:
    result = get_analysis(subject)
    if not result:
        return []
    return [group for group in result["recurring_groups"]
            if len(group["years"]) >= min_years]
