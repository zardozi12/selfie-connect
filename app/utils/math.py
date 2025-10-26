# app/utils/math.py
"""Safe mathematical operations to prevent logic bugs"""

def safe_cosine(a, b) -> float:
    """Safe cosine similarity that handles edge cases"""
    try:
        if not a or not b or len(a) != len(b):
            return 0.0
        a = [float(x) for x in a]
        b = [float(x) for x in b]
        n1 = sum(x*x for x in a) ** 0.5
        n2 = sum(y*y for y in b) ** 0.5
        if n1 == 0.0 or n2 == 0.0:
            if n1 == 0.0 and n2 == 0.0:
                return 1.0
            return 0.0
        result = sum(x * y for x, y in zip(a, b)) / (n1 * n2)
        # Clamp to [-1.0, 1.0] to avoid floating-point overshoot
        return max(-1.0, min(1.0, result))
    except Exception:
        return 0.0

def safe_normalize(vec) -> list[float]:
    try:
        if not vec:
            return []
        vec = [float(x) for x in vec]
        norm = sum(x*x for x in vec) ** 0.5
        if norm == 0.0:
            return [0.0] * len(vec)
        return [x / norm for x in vec]
    except Exception:
        return [0.0] * len(vec) if vec else []
