# tests/test_props.py
"""Property-based tests to catch logic bugs early"""

import pytest
from hypothesis import given, strategies as st
from app.services.embeddings import text_embedding
from app.services.encryption import new_data_key, fernet_from_dek
from app.utils.math import safe_cosine, safe_normalize
from app.utils.guard import in01


@given(st.text(min_size=1, max_size=80))
def test_text_embedding_len(s):
    """Text embeddings should always be 512 dimensions"""
    assert len(text_embedding(s)) == 512


@given(st.binary(min_size=0, max_size=256))
def test_encrypt_roundtrip(b):
    """Encryption should be lossless"""
    f = fernet_from_dek(new_data_key())
    assert f.decrypt(f.encrypt(b)) == b


@given(st.lists(st.floats(min_value=-10, max_value=10), min_size=1, max_size=100))
def test_safe_cosine_properties(vec):
    """Cosine similarity should be symmetric and bounded"""
    # Self-similarity should be 1.0
    assert abs(safe_cosine(vec, vec) - 1.0) < 1e-6
    
    # Should be symmetric
    vec2 = [x + 0.1 for x in vec]  # Small perturbation
    assert abs(safe_cosine(vec, vec2) - safe_cosine(vec2, vec)) < 1e-6
    
    # Should be bounded [-1, 1]
    result = safe_cosine(vec, vec2)
    assert -1.0 <= result <= 1.0


@given(st.lists(st.floats(min_value=-10, max_value=10), min_size=1, max_size=100))
def test_safe_normalize_properties(vec):
    """Normalized vectors should have unit length"""
    if not vec:
        return
    
    normalized = safe_normalize(vec)
    assert len(normalized) == len(vec)
    
    # Check unit length (within tolerance)
    norm = sum(x*x for x in normalized) ** 0.5
    assert abs(norm - 1.0) < 1e-6 or norm == 0.0


@given(st.floats(min_value=-1, max_value=2))
def test_guard_in01(x):
    """Guard should catch values outside [0,1]"""
    if 0.0 <= x <= 1.0:
        in01(x)  # Should not raise
    else:
        with pytest.raises(AssertionError):
            in01(x)


def test_face_box_normalization():
    """Face boxes should be properly normalized"""
    # Valid normalized face box
    fx, fy, fw, fh = 0.1, 0.2, 0.3, 0.4
    in01(fx, "face_x")
    in01(fy, "face_y") 
    in01(fw, "face_w")
    in01(fh, "face_h")
    
    # Invalid face box should raise
    with pytest.raises(AssertionError):
        in01(1.5, "face_x")  # Outside [0,1]
