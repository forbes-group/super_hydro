"""Testing some of the physics utilities."""
import pytest

import numpy as np

from super_hydro.physics import testing


def test_HO():
    with pytest.raises(ValueError):
        ho = testing.HO(unknown_parameter=6)
    ho = testing.HO(Nxy=(128, 256))

    metric = np.prod(ho.Lxy) / np.prod(ho.Nxy)

    # Check normalization
    for nx in range(4):
        for ny in range(4):
            E, psi = ho.get_eigenstate(nx, ny)
            n = abs(psi) ** 2
            N = n.sum() * metric
            assert np.allclose(N, 1)

    psi0 = ho.get_psi(t=0)
    N = (abs(psi0) ** 2).sum() * metric
    for t in [0.1, 1.0, 10.0]:
        psi = ho.get_psi(t=t)
        n = abs(psi) ** 2
        assert np.allclose(N, n.sum() * metric)
