"""A small rule engine for scoring records."""

OPERATORS = {
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
    "==": lambda a, b: a == b,
}


def apply_rule(record, field, operator, threshold):
    """Apply one comparison rule to a record field."""
    compare = OPERATORS[operator]
    return compare(record[field], threshold)


def score_record(record, rules):
    return sum(1 for rule in rules if apply_rule(record, *rule))
