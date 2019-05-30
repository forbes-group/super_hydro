"""Interfaces for various components of the system.
"""
from zope.interface import Interface, Attribute, classImplements


class IState(Interface):
    """Interface for physical model.

    This class represents a state of the physical system.  It is
    responsible for initializing and computing the time evolution of
    the system in response to external stimuli from the clients.
    """
    def __init__(Nxy, dt_t_scale, **kw):
        """Constructor.

        Should initialize the state.

        Arguments
        =========
        Nxy : (int, int)
           Size of grid.
        **kw:
          Additional arguments are system specific.
        """

    def get_density():
        """Return the density array."""

    def get_trace_particles():
        """Return the list of tracer particle positions."""

    def set(param, value):
        """Set the specified parameter.

        This is called interactively by the server.  Parameters could
        be implemented with properties, but our server explicitly
        calls this method to limit the require interface.
        """
