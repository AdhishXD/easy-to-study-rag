"""Compatibility facade for the saved full-context course analysis."""

import pandas as pd

from agents.analysis import get_analysis


def analyze_topic_frequency(top_n: int = 20, min_years: int = 1,
                            subject: str | None = None) -> pd.DataFrame:
    if not subject:
        raise ValueError("A subject is required for topic analysis")
    result = get_analysis(subject)
    if result is None:
        raise ValueError("Run 'Analyze teaching material and past papers' in the app first")
    rows = [
        {"term": topic["name"], "summary": topic["summary"],
         "num_years": topic["num_years"], "years": topic["years"]}
        for topic in result["topics"] if topic["num_years"] >= min_years
    ]
    return pd.DataFrame(rows, columns=["term", "summary", "num_years", "years"]).head(top_n)


def print_topic_report(df: pd.DataFrame) -> None:
    if df.empty:
        print("No topics meet the exam-year threshold.")
        return
    for _, row in df.iterrows():
        years = ", ".join(map(str, row["years"])) or "not seen in past papers"
        print(f"{row['term']} ({years}): {row['summary']}")
