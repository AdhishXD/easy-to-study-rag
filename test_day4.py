"""Read saved full-context analysis: python test_day4.py <subject>."""

import sys

from agents.pattern_agent import analyze_topic_frequency, print_topic_report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    report = analyze_topic_frequency(subject=sys.argv[1], min_years=1)
    print_topic_report(report)
