"""Shopping cart that totals items with the pricing module."""

from pricing import order_total


class Cart:
    def __init__(self):
        self.lines = []

    def add(self, unit_price, quantity):
        self.lines.append((unit_price, quantity))

    def total(self):
        return order_total(self.lines)
