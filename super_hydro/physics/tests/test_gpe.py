import numpy as np

import pytest

from ..gpe import State


def test_gpe():
    s = State(Nxy=(32, 64))
    assert s.data.shape == (32, 64)
    # assert np.allclose(s.data, np.sqrt(s.n0))
