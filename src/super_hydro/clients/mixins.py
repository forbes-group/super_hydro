"""Client mixins.

These mixins provide common functionality for various clients.
"""

from matplotlib import cm

__all__ = ["ClientDensityMixin"]


class ClientDensityMixin:
    """Basic client mixin with functions for manipulating density array."""

    @staticmethod
    def get_rgba_from_density(density):
        """Convert the density array into an rgba array for display.

        One must be a bit careful to transpose the arrays so that indexing works
        properly."""
        density = density[::-1].T
        # array = cm.viridis((n_-n_.min())/(n_.max()-n_.min()))
        array = cm.viridis(density / density.max())
        # array = self._update_frame_with_tracer_particles(array)
        array *= int(255 / array.max())  # normalize values
        rgba = array.astype(dtype="uint8")
        return rgba
