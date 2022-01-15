from contextlib import contextmanager
import logging
import os

import numpy as np
import scipy as sp

__all__ = ["expm2", "dot2"]


def expm2(M):
    """Return the matrix exponential of M over the first two indices.

    See: http://en.wikipedia.org/wiki/Matrix_exponential

    >>> from scipy.linalg import expm
    >>> np.random.seed(1)
    >>> M = np.random.random((2, 2, 5))
    >>> res = np.asarray([expm(M[:,:,_n]) for _n in range(M.shape[-1])])
    >>> res = np.rollaxis(res, 0, 3)
    >>> np.allclose(expm2(M), res)
    True
    """
    a = M[0, 0, ...]
    b = M[0, 1, ...]
    c = M[1, 0, ...]
    d = M[1, 1, ...]
    s = (a + d) / 2.0
    q = np.sqrt(0j + b * c - (a - s) * (d - s))
    exp_s = np.exp(s)
    exp_s_cosh_q = exp_s * np.cosh(q)
    exp_s_sinch_q = exp_s * sp.sinc(q * 1j / np.pi)
    _tmp = exp_s_cosh_q - s * exp_s_sinch_q
    A = _tmp + exp_s_sinch_q * a
    B = exp_s_sinch_q * b
    C = exp_s_sinch_q * c
    D = _tmp + exp_s_sinch_q * d
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
    return np.einsum("ab...,b...->a...", A, x)


def mstep(t, t1, alpha=3.0):
    r"""Smooth step function that goes from 0 at time ``t=0`` to 1 at time
    ``t=t1``.  This step function is $C_\infty$:
    """
    return np.where(
        t < 0.0,
        0.0,
        np.where(
            t < t1, (1 + np.tanh(alpha * np.tan(np.pi * (2 * t / t1 - 1) / 2))) / 2, 1.0
        ),
    )


class MyFormatter(logging.Formatter):
    """Custom logging formatter for sending info to Jupyter console."""

    def __init__(self):
        logging.Formatter.__init__(
            self,
            fmt="[%(levelname)s %(asctime)s super_hydro-%(name)s] %(message)s",
            datefmt="%H:%M:%S",
        )

    def format(self, record):
        record.levelname = record.levelname[0]
        msg = logging.Formatter.format(self, record)
        if record.levelno >= logging.WARNING:
            msg += "\n{}{}:{}".format(" " * 14, record.filename, record.lineno)
        return msg


class Logger:
    """Logging object."""

    def __init__(self, name="", indent_amount=2):
        self.name = name
        self.nesting = 0
        self.indent_amount = indent_amount

        # Logging to jupyter console.
        # Not exactly sure why this works, but here we add a handler
        # to send output to the main console.
        # https://stackoverflow.com/a/39331977/1088938
        logger = self.logger
        handler = None
        for h in logger.handlers:
            try:
                if h.stream.fileno() == 1:
                    handler = h
                    break
            except Exception:
                pass
        if not handler:
            handler = logging.StreamHandler(os.fdopen(1, "w"))
            logger.addHandler(handler)

        handler.setFormatter(MyFormatter())
        handler.setLevel("DEBUG")
        logger.setLevel("DEBUG")

    @property
    def logger(self):
        """Return the logger."""
        # Get logger each time so handlers are properly dealt with
        return logging.getLogger(self.name)

    @property
    def indent(self):
        """Return the appropriate indentation."""
        return " " * self.indent_amount * self.nesting

    def log(self, msg, level=logging.INFO):
        """Log msg to the logger."""
        # Get logger each time so handlers are properly dealt with
        self.logger.log(level=level, msg=self.indent + msg)

    def debug(self, msg, level=logging.DEBUG):
        """Log debug msg to the logger."""
        self.log(msg, level=level)

    def warning(self, msg, level=logging.WARNING):
        """Log warning msg to the logger."""
        self.log(msg, level=level)

    def error(self, msg, level=logging.ERROR):
        """Log error msg to the logger."""
        self.log(msg, level=level)

    def info(self, msg, level=logging.INFO):
        """Log error msg to the logger."""
        self.log(msg, level=level)

    @contextmanager
    def log_task(self, msg, level=logging.INFO):
        """Context for tasks with paired start and Done messages.

        Parameters
        ----------
        msg : str
           Message.  By default, results in messages like::

               msg...
               msg. Done.
               msg. Failed!

        level : int
           Logging level (default INFO)
        """
        self.log(msg + "...", level=level)
        try:
            self.nesting += 1
            yield
            self.nesting -= 1
            self.log(msg + ". Done.", level=level)
        except Exception:
            self.nesting -= 1
            self.log(msg + ". Failed!", level=logging.ERROR)
            raise


class PrintLogger(Logger):
    def log(self, msg, level=logging.INFO):
        """Log msg to the logger."""
        print(level, msg)
