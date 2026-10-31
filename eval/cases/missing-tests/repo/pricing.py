"""Pricing calculations for the shop."""

TAX_RATE = 0.2


def line_total(unit_price, quantity):
    return unit_price * quantity


def order_total(lines):
    subtotal = sum(line_total(price, qty) for price, qty in lines)
    return subtotal * (1 + TAX_RATE)
