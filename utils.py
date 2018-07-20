import numpy as np
import scipy as sp

__all__ = ['expm2', 'dot2']


def expm2(M):
    """Return the matrix exponential of M over the first two indices.

    See: http://en.wikipedia.org/wiki/Matrix_exponential

    >>> from scipy.linalg import expm
    >>> np.random.seed(1)
    >>> M = np.random.random((2, 2, 5))
    >>> res = np.asarray([expm(M[:,:,_n]) for _n in xrange(M.shape[-1])])
    >>> res = np.rollaxis(res, 0, 3)
    >>> np.allclose(expm2(M), res)
    True
    """
    a = M[0, 0, ...]
    b = M[0, 1, ...]
    c = M[1, 0, ...]
    d = M[1, 1, ...]
    s = (a + d)/2.0
    q = np.sqrt(0j + b*c - (a-s)*(d-s))
    exp_s = np.exp(s)
    exp_s_cosh_q = exp_s*np.cosh(q)
    exp_s_sinch_q = exp_s*sp.sinc(q*1j/np.pi)
    _tmp = exp_s_cosh_q - s*exp_s_sinch_q
    A = _tmp + exp_s_sinch_q*a
    B = exp_s_sinch_q*b
    C = exp_s_sinch_q*c
    D = _tmp + exp_s_sinch_q*d
    return np.asarray([[A, B], [C, D]])


def dot2(A, x):
    """Return the matrix multiplication of A*x over the second index
    of A and the first index of x.

    >>> from scipy.linalg import expm
    >>> np.random.seed(1)
    >>> A = np.random.random((2, 2, 5))
    >>> x = np.random.random((2, 5))
    >>> res = (A*x[None, ...]).sum(axis=1)
    >>> np.allclose(dot2(A, x), res)
    True
    """
    return np.einsum('ab...,b...->a...', A, x)
