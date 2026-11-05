"""A tiny 'application under test' for the demo. One bug here has been fixed; one has not."""


def apply_discount(price: float, percent: float) -> float:
    # BUG-001 (fixed): discounts over 100% used to produce negative prices.
    percent = min(max(percent, 0), 100)
    return round(price * (1 - percent / 100), 2)


def cart_total(prices: list, tax_rate: float = 0.08) -> float:
    # BUG-002 (still open): tax is rounded per item instead of on the subtotal,
    # so totals drift by a cent on some carts.
    return sum(round(p * (1 + tax_rate), 2) for p in prices)
