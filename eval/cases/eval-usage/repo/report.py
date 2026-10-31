"""Reports built on rule scores."""

from rules import score_record


def summarise(records, rules):
    passed = [r for r in records if score_record(r, rules) == len(rules)]
    return {"total": len(records), "passed": len(passed)}
