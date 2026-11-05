"""BUG-001: a discount above 100% must not produce a negative price. Exit 0 = fixed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from shop import apply_discount  # noqa: E402

price = apply_discount(50.0, 150)
print(f"apply_discount(50, 150) = {price}")
sys.exit(0 if price >= 0 else 1)
