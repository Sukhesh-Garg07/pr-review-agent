from rules import apply_rule, score_record


def test_apply_rule():
    assert apply_rule({"age": 30}, "age", ">", 18)


def test_score_record():
    rules = [("age", ">", 18), ("age", "<", 65)]
    assert score_record({"age": 30}, rules) == 2
