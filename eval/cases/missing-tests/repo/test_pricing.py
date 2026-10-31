from pricing import line_total, order_total


def test_line_total():
    assert line_total(10, 3) == 30


def test_order_total_includes_tax():
    assert order_total([(10, 2)]) == 24.0
