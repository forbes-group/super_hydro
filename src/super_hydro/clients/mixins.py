"""Client mixins.

These mixins provide common functionality for various clients.
"""

from matplotlib import cm

__all__ = ["DensityMixin"]


class DensityMixin:
    """Basic client mixin with functions for manipulating density array."""

    @staticmethod
    def get_rgba_from_density(density):
        """Convert the density array into an rgba array for display."""
        density = density[::-1].T
        # array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array = cm.viridis(density / density.max())
        # array = self._update_frame_with_tracer_particles(array)
        array *= int(255 / array.max())  # normalize values
        rgba = array.astype(dtype="uint8")
        return rgba
