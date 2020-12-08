"""Various useful contexts.
"""
import functools
import os
import signal
import time

import threading

import warnings


def is_main_thread():
    """Return True if this is the main thread."""
    return threading.current_thread() is threading.main_thread()


class NoInterrupt(object):
    """Suspend the various signals during the execution block and a
    simple mechanism to allow threads to be interrupted.

    Arguments
    ---------
    ignore : bool
       If True, then do not raise a KeyboardInterrupt if a soft interrupt is
       caught unless forced by multiple interrupt requests in a
       limited time.

    There are two main entry points: globally by calling the suspend()
    method, and within a NoInterrupt() context.

    Main Thread
    -----------
    When executed in a context from the main thread, a signal handler
    is established which captures interrupt signals and represents
    them instead as a boolean flag (conventionally called
    "interrupted").

    Global interrupt suppression can be enabled by creating a
    NoInterrupt() instance and calling suspend().  This will stay in
    effect until restore() is called, a forcing interrupt is received,
    or the instance is deleted.  Additional calls to suspend() will
    reinstall the handlers, but they will not be nested.

    Interrupts can also be suspended in contexts.  These can be
    nested.  These instances will become False at the end of the
    context.
    
    Auxiliary Threads
    -----------------
    Auxiliary threads can create instances of NoInterrupt() or use
    contexts, but cannot call suspend() or restore().  In these cases
    the context does not suspend signals (see below), but the flag is
    still useful as it can act as a signal force the auxiliary thread
    to terminate if an interrupt is received in the main thread.

    A couple of notes about using the context in auxiliary threads.

    1. Either suspend() must be called globally or a context must
       first be created in the main thread - otherwise the signal
       handlers will not be installed.  An exception will be raised if
       an auxiliary thread tries to create a context without the
       handlers being installed.
       this case.
    2. As stated in the python documents, signal handlers are always
       executed in the main thread.  Likewise, only the main thread is
       allowed to set new signal handlers.  Thus, the signal
       interrupting facilities provided here only work properly in the
       main thread.  Also, forcing an interrupt cannot raise an
       exception in the auxiliary threads: one must wait for them to
       respond to the changed "interrupted" value.

       For more information about killing threads see:

       * http://stackoverflow.com/questions/323972/
         is-there-any-way-to-kill-a-thread-in-python

    Attributes
    ----------
    force_n : int
       Number of interrupts to force signal.
    force_timeout : float
       Time in which force_n interrupts must be received to trigger a
       forced interrupt.

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
    >>> try:  # All doctests need to be wrapped in try blocks to not kill py.test!
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
    KeyboardInterrupt:
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
    # Each time a signal is raised, it is inserted into the
    # _signals_raised dict and the corresponding entry of
    # _signal_count is incremented.  At the end of the final context
    # of the main thread (outermost context) the dict of
    # _signals_raised is cleared, but _signal_count is NOT reset.  The
    # value of _signal_count is stored in each instance to allow that
    # instance to determined if a signal was raised in that context
    # allowing threads to use the interrupted flag even if there is no
    # active context in the main thread.
    
    _instances = set()
    _original_handlers = {}     # Dictionary of original handlers
    _signals_raised = {}        # Dictionary if signals raised
    _signal_count = {}          # Dictionary of signal counts
    _signals = set((signal.SIGINT, signal.SIGTERM))
    _signals_suspended = set()
    
    # Time, in seconds, for which force_n successive interrupts will
    # toggle the default handler.
    force_n = 3
    force_timeout = 1

    # Lock should be re-entrant (I think) since a signal might be sent during
    # operation of one of the functions.
    _lock = threading.RLock()

    def __init__(self, ignore=True):
        with self._lock:
            self.ignore = ignore
            self._active = True
            self.signal_count_at_start = dict(self._signal_count)

    @classmethod
    def is_registered(cls):
        """Return True if handlers are registered."""
        with cls._lock:
            registered = bool(cls._signals.intersection(cls._original_handlers))
            if False and registered:
                assert all([
                    signal.getsignal(_signum) == cls.handle_signal
                    for _signum in cls._original_handlers])
            return registered

    @classmethod
    def register(cls):
        """Register the handlers so that signals can be suspended."""
        if not is_main_thread():
            _msg = " ".join([
                "Can only register handlers from the main thread."
                "(Called from thread {})".format(threading.get_ident())])
            raise RuntimeError(_msg)
        
        with cls._lock:
            if not cls.is_registered():
                cls._original_handlers = {
                    _signum: signal.signal(_signum, cls.handle_signal)
                    for _signum in cls._signals}
            assert cls.is_registered()
            
    @classmethod
    def unregister(cls, full=False):
        """Reset handlers to the original values.  No more signal suspension.

        Arguments
        ---------
        full : bool
           If True, do a full reset, including counts.
        """
        with cls._lock:
            while cls._original_handlers:
                _signum, _handler = cls._original_handlers.popitem()
                signal.signal(_signum, _handler)

            if full:
                cls.reset()
                cls._signal_count = {}
                
            if not full:
                assert not cls.is_registered()

    @classmethod
    def set_signals(cls, signals):
        """Change the signal handlers.
        
        Note: This does not change the signals listed in _suspended_signals list.

        Arguments
        ---------
        signals : set()
           Set of signal numbers.
        """
        signals = set(signals)
        with cls._lock:
            if cls.is_registered() and signals != cls._signals:
                cls.unregister()
                cls._signals = set(signals)
                cls.register()
                
    @classmethod
    def suspend(cls, signals=None):
        """Suspends the specified signals."""
        with cls._lock:
            if signals is None:
                signals = cls._signals
                for signum in signals:
                    if signum not in cls._original_handlers:
                        warnings.warn(
                            " ".join([
                                "No handler registered for signal {}.",
                                "Signal will not be suspended."])
                            .format(signum))
                    cls._signals_suspended.add(signum)

    @classmethod
    def resume(cls, signals=None):
        """Resumes the specified signals."""
        if signals is None:
            signals = set(cls._signals_suspended)
        for signum in signals:
            cls._signals_suspended.discard(signum)

    @classmethod
    def reset(cls):
        """Reset the signal logs and return last signal `(signum, frame, time)`.
        """
        res = None
        with cls._lock:
            if hasattr(cls, '_last_signal'):
                res = cls._last_signal
                del cls._last_signal
            cls._signals_raised = {}

        return(res)
    
    @classmethod
    def handle_signal(cls, signum, frame):
        """Custom signal handler.

        This stores the signal for later processing unless it was
        forced or there are no current contexts, in which case the
        original handlers will be called.
        """
        with cls._lock:
            cls._last_signal = (signum, frame, time.time())
            cls._signals_raised.setdefault(signum, [])
            cls._signals_raised[signum].append(cls._last_signal)
            cls._signal_count.setdefault(signum, 0)
            cls._signal_count[signum] += 1
            if (cls._forced_interrupt(signum)
                    or signum not in cls._signals_suspended):
                cls.handle_original_signal(signum=signum, frame=frame)

    @classmethod
    def handle_original_signal(cls, signum, frame):
        """Call the original handler."""
        # This is a bit tricky because python does not provide a
        # default handler for SIGTERM so we can't simply use it.
        handler = cls._original_handlers[signum]
        if handler:
            handler(signum, frame)
        else:
            if cls.is_registered():
                cls.unregister()
                os.kill(os.getpid(), signum)
                cls.register()
            else:
                os.kill(os.getpid(), signum)

    @classmethod
    def _forced_interrupt(cls, signum):
        """Return True if `force_n` interrupts have been recieved in the past
        `force_timeout` seconds"""
        with cls._lock:
            signals_raised = cls._signals_raised.get(signum, [])
            return (cls.force_n <= len(signals_raised)
                    and cls.force_timeout > (signals_raised[-1][-1]
                                             - signals_raised[-cls.force_n][-1]))

    #############
    # Dummy handlers to thwart ipykernel's attempts to restore the
    # default signal handlers.
    # https://github.com/ipython/ipykernel/issues/328
    @staticmethod
    def _pre_handler_hook():
        pass
    
    @staticmethod
    def _post_handler_hook():
        pass
    
    def __enter__(self):
        """Enter context."""
        with self._lock:
            try:
                import IPython
                kernel = IPython.get_ipython().kernel
                kernel.pre_handler_hook = self._pre_handler_hook
                kernel.post_handler_hook = self._post_handler_hook
            except (ImportError, AttributeError):
                pass
            
            self._active = True
            self.signal_count_at_start = dict(self._signal_count)
            if is_main_thread():
                if not self.is_registered():
                    self.register()
                self.suspend()
                NoInterrupt._instances.add(self)
            elif not self.is_registered():
                    _msg = "\n".join([
                        "Thread {} entering unregistered NoInterrupt() context.",
                        "Interrupts will not be processed!  "
                        + "Call register() in main thread."
                    ]).format(threading.get_ident())
                    warnings.warn(_msg)
            
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self._lock:
            self._active = False
            if not is_main_thread():
                return
            
            self._instances.remove(self)
            if not self._instances:
                # Only raise an exception if all the instances have been
                # cleared, otherwise we might still be in a protected
                # context somewhere.

                self.resume()
                last_signal = self.reset()
                
                if last_signal and not self.ignore:
                    # Call original handler.
                    signum, frame, _time = last_signal
                    self.handle_original_signal(signum=signum, frame=frame)
            try:
                import IPython
                kernel = IPython.get_ipython().kernel
                del kernel.pre_handler_hook
                del kernel.post_handler_hook
            except (ImportError, AttributeError):
                pass

    def __bool__(self):
        """Return True if interrupted."""
        with self._lock:
            return (
                not self._active
                or any([
                    self._signal_count.get(_signum, 0)
                    > self.signal_count_at_start.get(_signum, 0)
                    for _signum in self._signals]))

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
    """Decorator that suspends signals and passes an interrupted flag
    to the protected function.  Can only be called from the main
    thread: will raise a RuntimeError otherwise (use `@interrupted` instead).

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
    _msg = " ".join(
        "@nointerrupt function called from non-main thread {}."
        "(Use @interrupt instead).")
    
    @functools.wraps(f)
    def wrapper(*v, **kw):
        if not is_main_thread():
            raise RuntimeError(_msg.format(threading.get_ident()))
        with NoInterrupt() as interrupted:
            kw.setdefault('interrupted', interrupted)
            return f(*v, **kw)
    return wrapper


class CoroutineWrapper(object):
    """Wrapper for coroutine contexts that allows them to function as a context
    but also as a function.  Similar to open() which may be used both in a
    function or as a file object.  Note: be sure to call close() if you do not
    use this as a context.
    """
    def __init__(self, coroutine):
        self.coroutine = coroutine
        self.started = False

    def __enter__(self, *v, **kw):
        self.res = next(self.coroutine)   # Prime the coroutine
        self.started = True
        return self.send

    def __exit__(self, type, value, tb):
        self.close()
        return

    def send(self, *v):
        self.res = self.coroutine.send(*v)
        return self.res

    def __call__(self, *v):
        if not self.started:
            self.__enter__()
        return self.send(*v)

    def close(self):
        self.coroutine.close()


def coroutine(coroutine):
    """Decorator for a context that yeilds an function from a coroutine.

    This allows you to write functions that maintain state between calls.  The
    use as a context here ensures that the coroutine is closed.

    Examples
    --------
    Here is an example based on that suggested by Thomas Kluyver:
    http://takluyver.github.io/posts/readable-python-coroutines.html

    >>> @coroutine
    ... def get_have_seen(case_sensitive=False):
    ...     seen = set()    # Set of words already seen.  This is the "state"
    ...     word = (yield)
    ...     while True:
    ...         if not case_sensitive:
    ...             word = word.lower()
    ...         result = word in seen
    ...         seen.add(word)
    ...         word = (yield result)
    >>> with get_have_seen(case_sensitive=False) as have_seen:
    ...     print(have_seen("hello"))
    ...     print(have_seen("hello"))
    ...     print(have_seen("Hello"))
    ...     print(have_seen("hi"))
    ...     print(have_seen("hi"))
    False
    True
    True
    False
    True
    >>> have_seen("hi")
    Traceback (most recent call last):
       ...
    StopIteration

    You can also use this as a function (like open()) but don't forget to close
    it.
    >>> have_seen = get_have_seen(case_sensitive=True)
    >>> have_seen("hello")
    False
    >>> have_seen("hello")
    True
    >>> have_seen("Hello")
    False
    >>> have_seen("hi")
    False
    >>> have_seen("hi")
    True
    >>> have_seen.close()
    >>> have_seen("hi")
    Traceback (most recent call last):
       ...
    StopIteration

    """
    # @contextlib.contextmanager
    @functools.wraps(coroutine)
    def wrapper(*v, **kw):
        return CoroutineWrapper(coroutine(*v, **kw))
        # primed_coroutine = coroutine(*v, **kw)
        # next(primed_coroutine)
        # yield primed_coroutine.send
        # primed_coroutine.close()
    return wrapper
