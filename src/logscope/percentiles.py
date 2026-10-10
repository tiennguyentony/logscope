from __future__ import annotations

from collections.abc import Sequence


def parse_percentiles(spec: str) -> list[float]:
    """'50,95,99.9' -> [50.0, 95.0, 99.9]. Each must be in (0, 100]."""
    result: list[float] = []
    for token in spec.split(","):
        token = token.strip().removeprefix("p")
        try:
            p = float(token)
        except ValueError:
            raise ValueError(f"bad percentile {token!r}; use e.g. 50,95,99") from None
        if not 0 < p <= 100:
            raise ValueError(f"percentile {token} is out of range; must be in (0, 100]")
        result.append(p)
    return result


def percentile(sorted_values: Sequence[float], p: float) -> float:
    """Return the p-th percentile of an already sorted, non-empty sequence.

    Uses linear interpolation between the two closest ranks, the same as
    numpy.percentile's default, so numbers match what people get in a
    notebook.
    """
    if not sorted_values:
        raise ValueError("percentile of an empty sequence")
    index = int(len(sorted_values) * p / 100)
    return sorted_values[index]
