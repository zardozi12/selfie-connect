# app/utils/guard.py

def in01(x: float, name: str = "value"):
    """Assert that a value is normalized between 0 and 1"""
    assert 0.0 <= x <= 1.0, f"{name} not normalized [0,1]: {x}"

def same_len(a, b, name_a="a", name_b="b"):
    """Assert that two sequences have the same length"""
    assert len(a) == len(b), f"len({name_a})={len(a)} != len({name_b})={len(b)}"

def non_empty(seq, name: str = "sequence"):
    """Assert that a sequence is not empty"""
    assert len(seq) > 0, f"{name} is empty"

def positive(x: float, name: str = "value"):
    """Assert that a value is positive"""
    assert x > 0, f"{name} must be positive: {x}"
