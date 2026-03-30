from __future__ import annotations


def clamp(value: float, lower: float, upper: float) -> float:
    if lower > upper:
        raise ValueError("lower bound cannot exceed upper bound")
    return max(lower, min(value, upper))
