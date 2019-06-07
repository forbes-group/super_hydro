"""Provides the NoInterrupt context from the mmfutils project.
"""
import functools
import signal
import time

from threading import RLock


class NoInterrupt(object):
    """Suspend the various signals during the execution block.

    Arguments
    ---------
    ignore : bool
       If True, then do not raise a KeyboardInterrupt if a soft interrupt is
       caught.

    Note: This is not yet threadsafe.  Semaphores should be used so that the
      ultimate KeyboardInterrupt is raised only by the outer-most context (in
      the main thread?)  The present code works for a single thread because the
      outermost context will return last.

      See:

      * http://stackoverflow.com/questions/323972/
        is-there-any-way-to-kill-a-thread-in-python

    Examples
    --------
    The simplest use-cases look like these:

    Simple context:

    >>> with NoInterrupt():
    ...    pass             # do something

    Context with a cleanly aborted loop:

    >>> with NoInterrupt() as interrupted:
    ...     done = False
    ...     while not interrupted and not done:
    ...         # Do something
    ...         done = True

    Map:

    >>> NoInterrupt().map(abs, [1, -1, 2, -2])
    [1, 1, 2, 2]

    Keyboard interrupt signals are suspended during the execution of
    the block unless forced by the user (3 rapid interrupts within
    1s).  Interrupts are ignored by default unless `ignore=False` is
    specified, in which case they will be raised when the context is
    ended.

    If you want to control when you exit the block, use the
    `interrupted` flag. This could be used, for example, while
    plotting frames in an animation (see doc/Animation.ipynb).
    Without the NoInterrupt() context, if the user sends a keyboard
    interrupt to the process while plotting, at best, a huge
    stack-trace is produced, and at worst, the kernel will crash
    (randomly depending on where the interrupt was received).  With
    this context, the interrupt will change `interrupted` to True so
    you can exit the context when it is safe.

    The last case is mapping a function to data.  This will allow the
    user to interrupt the process between function calls.

    Note that NoInterrupt() contexts can be nested, so if you have
    sensitive code, just wrap it in a context without worrying about
    whether or not the calling code is also wrapping.

    In the following examples we demonstrate this by simulating
    interrupts

    >>> import os, signal, time
    >>> def simulate_interrupt(force=False):
    ...     os.kill(os.getpid(), signal.SIGINT)
    ...     if force:
    ...         # Simulated a forced interrupt with multiple signals
    ...         os.kill(os.getpid(), signal.SIGINT)
    ...         os.kill(os.getpid(), signal.SIGINT)
    ...     time.sleep(0.1)   # Wait so signal can be received predictably

    This loop will get interrupted in the middle so that m and n will not be
    the same.

    >>> def f(n, interrupted=False, force=False, interrupt=True):
    ...     while n[0] < 10 and not interrupted:
    ...         n[0] += 1
    ...         if n[0] == 5 and interrupt:
    ...             simulate_interrupt(force=force)
    ...         n[1] += 1

    >>> n = [0, 0]
    >>> f(n, interrupt=False)
    >>> n
    [10, 10]

    >>> n = [0, 0]
    >>> try:  # All doctests wrapped in try blocks to not kill py.test!
    ...     f(n)
    ... except KeyboardInterrupt as err:
    ...     print("KeyboardInterrupt: {}".format(err))
    KeyboardInterrupt:
    >>> n
    [5, 4]

    Now we protect the loop from interrupts.
    >>> n = [0, 0]
    >>> try:
    ...     with NoInterrupt(ignore=False) as interrupted:
    ...         f(n)
    ... except KeyboardInterrupt as err:
    ...     print("KeyboardInterrupt: {}".format(err))
    KeyboardInterrupt:
    >>> n
    [10, 10]

    One can ignore the exception if desired (this is the default as of 0.4.11):
    >>> n = [0, 0]
    >>> with NoInterrupt() as interrupted:
    ...     f(n)
    >>> n
    [10, 10]

    Three rapid exceptions will still force an interrupt when it occurs.  This
    might occur at random places in your code, so don't do this unless you
    really need to stop the process.
    >>> n = [0, 0]
    >>> try:
    ...     with NoInterrupt(ignore=False) as interrupted:
    ...         f(n, force=True)
    ... except KeyboardInterrupt as err:
    ...     print("KeyboardInterrupt: {}".format(err))
    KeyboardInterrupt: Interrupt forced
    >>> n
    [5, 4]


    If `f()` is slow, we might want to interrupt it at safe times.  This is
    what the `interrupted` flag is for:

    >>> n = [0, 0]
    >>> try:
    ...     with NoInterrupt(ignore=False) as interrupted:
    ...         f(n, interrupted)
    ... except KeyboardInterrupt as err:
    ...     print("KeyboardInterrupt: {}".format(err))
    KeyboardInterrupt:
    >>> n
    [5, 5]

    Again: the exception can be ignored
    >>> n = [0, 0]
    >>> with NoInterrupt() as interrupted:
    ...     f(n, interrupted)
    >>> n
    [5, 5]

    """
    _instances = set()  # Instances of NoInterrupt suspending signals
    _signals = set((signal.SIGINT, signal.SIGTERM))
    _signal_handlers = {}  # Dictionary of original handlers
    _signals_raised = []
    _force_n = 3

    # Time, in seconds, for which 3 successive interrupts will raise a
    # KeyboardInterrupt
    _force_timeout = 1

    # Lock should be re-entrant (I think) since a signal might be sent during
    # operation of one of the functions.
    _lock = RLock()

    @classmethod
    def catch_signals(cls, signals=None):
        """Set signals and register the signal handler if there are any
        interrupt instances."""
        with cls._lock:
            if signals:
                cls._signals = set(signals)
                cls._reset_handlers()

            if cls._instances:
                # Only set the handlers if there are interrupt instances
                cls._set_handlers()

    @classmethod
    def _set_handlers(cls):
        with cls._lock:
            cls._reset_handlers()
            for _sig in cls._signals:
                cls._signal_handlers[_sig] = signal.signal(
                    _sig, cls.handle_signal)

    @classmethod
    def _reset_handlers(cls):
        with cls._lock:
            for _sig in list(cls._signal_handlers):
                signal.signal(_sig, cls._signal_handlers.pop(_sig))

    @classmethod
    def handle_signal(cls, signum, frame):
        with cls._lock:
            cls._signals_raised.append((signum, frame, time.time()))
            if cls._forced_interrupt():
                raise KeyboardInterrupt("Interrupt forced")

    @classmethod
    def _forced_interrupt(cls):
        """Return True if `_force_n` interrupts have been recieved in the past
        `_force_timeout` seconds"""
        with cls._lock:
            return (cls._force_n <= len(cls._signals_raised)
                    and cls._force_timeout > (cls._signals_raised[-1][-1]
                                              - cls._signals_raised[-3][-1]))

    def __init__(self, ignore=True):
        self.ignore = ignore

    def __enter__(self):
        NoInterrupt._instances.add(self)
        self.catch_signals()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self._lock:
            self._instances.remove(self)
            if not self._instances:
                # Only raise an exception if all the instances have been
                # cleared, otherwise we might still be in a protected
                # context somewhere.
                self._reset_handlers()
                if self:
                    # An interrupt was raised.
                    while self._signals_raised:
                        # Clear previous signals
                        self._signals_raised.pop()
                    if exc_type is None and not self.ignore:
                        raise KeyboardInterrupt()

    @classmethod
    def __bool__(cls):
        with cls._lock:
            return bool(cls._signals_raised)

    __nonzero__ = __bool__      # For python 2.

    def map(self, function, sequence, *v, **kw):
        """Map function onto sequence until interrupted or done.

        Interrupts will not occur inside function() unless forced.
        """
        res = []
        with self as interrupted:
            for s in sequence:
                if interrupted:
                    break
                res.append(function(s, *v, **kw))
        return res


def nointerrupt(f):
    """Decorator that passes an interrupted flag to the protected
    function.

    Examples
    --------
    >>> @nointerrupt
    ... def f(interrupted):
    ...     for n in range(3):
    ...         if interrupted:
    ...             break
    ...         print(n)
    ...         time.sleep(0.1)
    >>> f()
    0
    1
    2
    """
    @functools.wraps(f)
    def wrapper(*v, **kw):
        with NoInterrupt() as interrupted:
            kw.setdefault('interrupted', interrupted)
            return f(*v, **kw)
    return wrapper
