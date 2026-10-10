import math

import pytest

from app.embedding_smoke import validate_vectors


def test_embedding_contract_rejects_wrong_size_nonfinite_and_unnormalized():
    valid = [1.0] + [0.0] * 767
    validate_vectors([valid, valid])
    for invalid in ([1.0] * 767, [math.nan] + valid[1:], [2.0] + valid[1:]):
        with pytest.raises(ValueError):
            validate_vectors([valid, invalid])
