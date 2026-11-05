"""BUG-002: tax must be applied to the subtotal, not rounded per item. Exit 0 = fixed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shop import cart_total  # noqa: E402

prices = [0.05, 0.05, 0.05]
expected = round(sum(prices) * 1.08, 2)   # 0.16
actual = round(cart_total(prices), 2)     # 0.15 while the bug exists
print(f"cart_total({prices}) = {actual}, expected {expected}")
sys.exit(0 if actual == expected else 1)
