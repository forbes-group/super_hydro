"""Simple synthesizer.  We use this to demonstrate latency issues with the interface.
"""
import numpy as np
from scipy.interpolate import UnivariateSpline

import pyaudio

from .contexts import NoInterrupt


class Synthesizer:
    """Simple synthesizer class.

    To prevent clipping, we keep track of the oscillator phase, ensuring that a complete
    cycle is played before switching frequencies.

    This generates a continuous pitch of frequency `pitch*freq_440_Hz`.

    Usage
    -----
    Here is an example of using the synthesizer in a context to play 12 semitones for
    0.2s each using equal temperament (12-TET).

    >>> import time
    >>> tic = time.time()
    >>> for n in range(13):
    ...     time.sleep(0.2)
    >>> print((time.time() - tic)/13)

    >>> import time
    >>> tic = time.time()
    >>> with Synthesizer() as s:
    ...    for n in range(13):
    ...        s.pitch = 2**(n/12)
    ...        time.sleep(0.2)
    >>> print((time.time() - tic)/13)

    One can also directly "play" notes:

    >>> s = Synthesizer()
    >>> tic = time.time()
    >>> for n in range(13):
    ...     s.play(n, 0.2)
    >>> print((time.time() - tic)/13)
    >>> del s
    """

    sample_rate = 44100  # Same rate in Hz
    # sample_rate = 8820
    sample_type = np.int16
    channels = 1
    clip = False  # Clip audio, or scale down.
    freq_440_Hz = 440.0  # Tuning
    _pitch = 1.0
    t = 0.0
    asynchronous = False
    waveform = "custom"
    normalize = False
    volume = 0.3

    # These define the custom waveform.
    phis = 2 * np.pi * np.array([0, 0.1, 0.4, 0.6, 0.9, 1.0])
    As = np.array([0, 0, 1, -1, 0, 0])
    smooth = 0.01

    # Timeout in seconds when using as a context.
    timeout = None

    def __init__(self, **kw):
        for key in kw:
            if not hasattr(self, key):
                raise NotImplementedError(f"Unknown parameter {key}.")
            setattr(self, key, kw[key])
        self.init()

    def init(self):
        self.p = pyaudio.PyAudio()
        self.format = self.p.get_format_from_width(width=self.sample_type().itemsize)
        self.max = np.iinfo(self.sample_type).max
        self.interrupted = False
        args = dict(
            rate=self.sample_rate,
            format=self.format,
            channels=self.channels,
            output=True,
        )
        if self.asynchronous:
            args["stream_callback"] = self.callback
        self.stream = self.p.open(**args)

        # Create a custom oscillator
        spl = UnivariateSpline(self.phis, self.As, k=1, s=0)
        if self.smooth > 0:
            phi = np.linspace(0, 2 * np.pi)
            spl = UnivariateSpline(phi, spl(phi), k=3, s=self.smooth)
        self.spl = spl
        self._phase = 0

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, pitch):
        if self.normalize:
            pitch = 2 ** (np.log2(pitch) % 1.0)
        self._pitch = pitch

    def callback(self, input_data, frame_count, time_info, status_flag):
        if self.interrupted:
            return (None, pyaudio.paComplete)
        return (self.get_frames(frame_count=frame_count), pyaudio.paContinue)

    def osc(self, phi):
        """Return the oscilator shape."""
        if self.waveform == "triangle":
            T = 2 * np.pi
            return 1 - 4 * abs(((phi + T / 4) % T) / T - 0.5)
        elif self.waveform == "saw":
            T = 2 * np.pi
            return 2 * ((phi - T / 2) % T) / T - 1
        elif self.waveform == "sin":
            return np.sin(phi)
        else:
            return self.spl(phi)

    def get_frames(self, frame_count):
        T = frame_count / self.sample_rate
        w = 2 * np.pi * self.freq_440_Hz * self.pitch
        t = self.t + np.arange(frame_count) / self.sample_rate
        phase = (self._phase - w * self.t) % (2 * np.pi)
        self.t += T
        signal = self.volume * self.osc((w * t + phase) % (2 * np.pi))
        self._phase = (w * self.t + phase) % (2 * np.pi)
        return self.encode(signal)

    def encode(self, signal):
        if self.clip:
            signal = np.minimum(np.maximum(signal, 1.0), -1.0)
        else:
            signal /= max(np.abs(signal).max(), 1.0)
        frames = (signal * self.max).astype(self.sample_type)
        return frames

    def play(self, note=0.0, duration=2.0):
        frame_count = int(self.sample_rate * duration)
        self.pitch = 2 ** (note / 12)
        frames = self.get_frames(frame_count)
        self.stream.write(frames, num_frames=frame_count)

    # Context manager for asynchronous stream.
    def __enter__(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.asynchronous = True
        self.init()

        NoInterrupt.unregister()
        self.interrupted = NoInterrupt(timeout=self.timeout).__enter__()
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        if hasattr(self.interrupted, "__exit__"):
            self.interrupted.__exit__(exc_type, exc_value, traceback)
        self.stop()

    def stop(self):
        self.interrupted = False
        if pyaudio.pa and self.stream:
            # Strange bug: pyaudio somehow sets pa to None atexit, causing this to fail
            # unless we bail
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def __del__(self):
        self.__exit__()


def notebook_synth(timeout=5, **kw):
    """Run the synthesizer in a Jupyter notebook."""
    import time
    from IPython.display import display
    from ipywidgets import FloatSlider, VBox  # , HTML, Label
    from .contexts import NoInterrupt

    # from ipyevents import Event

    s = Synthesizer(timeout=timeout, **kw)

    def on_freq(event):
        if event["type"] == "change":
            s.pitch = event["owner"].value / s.freq_440_Hz

    freq = FloatSlider(value=328.0, min=110.0, max=880.0, description="Freq. (Hz)")
    freq.observe(on_freq)
    # display(VBox([freq, l]), h)
    display(VBox([freq]))

    s.__enter__()
    return s


def tkinter_synth(timeout=5, **kw):
    """TkInter version of the synthesizer."""
    import time

    # from tkinter import *
    from tkinter import Tk, ttk, N, S, E, W, StringVar

    with Synthesizer(timeout=timeout, **kw) as s:

        def update_freq(freq):
            s.pitch = float(freq) / s.freq_440_Hz

        root = Tk()
        root.title("Synthesizer")

        mainframe = ttk.Frame(root, padding="3 3 12 12")
        mainframe.grid(column=0, row=0, sticky=(N, W, E, S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        freq = StringVar()
        freq_entry = ttk.Scale(
            mainframe,
            length=200,
            from_=110.0,
            to=880.0,
            variable=freq,
            command=update_freq,
        )
        freq_entry.grid(column=2, row=1)

        ttk.Label(mainframe, text="Freq. (Hz)").grid(column=3, row=1, sticky=W)
        ttk.Label(mainframe, textvariable=freq, width=10).grid(
            column=1, row=1, sticky=E
        )

        for child in mainframe.winfo_children():
            child.grid_configure(padx=5, pady=5)

        freq_entry.focus()

        while not s.interrupted:
            root.update_idletasks()
            root.update()
        root.withdraw()
        root.destroy()
        # root.mainloop()
