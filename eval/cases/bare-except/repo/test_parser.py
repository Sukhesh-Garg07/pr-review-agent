from parser import parse_batch, parse_record


def test_parse_record():
    record = parse_record('{"id": 1, "value": "x"}')
    assert record == {"id": 1, "value": "x"}


def test_parse_batch():
    records = parse_batch(['{"id": 1, "value": "a"}', '{"id": 2, "value": "b"}'])
    assert [r["id"] for r in records] == [1, 2]
