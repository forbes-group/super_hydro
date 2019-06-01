"""Interfaces for various components of the system.
"""
from zope.interface import Interface, Attribute, classImplements


class IModel(Interface):
    """Interface for physical model.

    This class represents a state of the physical system.  It is
    responsible for initializing and computing the time evolution of
    the system in response to external stimuli from the clients.
    """
    def __init__(Nxy, opts):
        """Constructor.

        Should initialize the state.

        Arguments
        =========
        opts : Options
           Options object with attributes defined through the
           configuration mechanism.
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
