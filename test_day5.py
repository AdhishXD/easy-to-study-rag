"""Generate a quiz from saved analysis: python test_day5.py <subject>."""

import json
import sys
from datetime import datetime, timezone

from agents.quiz_agent import generate_quiz, print_quiz


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    quiz = generate_quiz(top_n_topics=5, questions_per_topic=2, subject=sys.argv[1])
    print_quiz(quiz)
    with open("generated_quiz.json", "w", encoding="utf-8") as stream:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(),
                   "questions": quiz}, stream, indent=2, ensure_ascii=False)
