"""Interfaces for various components of the system.
"""
from zope.interface import Interface, Attribute, classImplements


class IModel(Interface):
    """Interface for physical model.

    This class represents a state of the physical system.  It is
    responsible for initializing and computing the time evolution of
    the system in response to external stimuli from the clients.

    The model can define a set of parameters which should be specified
    along with their default values through the `params` attribute.

    A subset of these can be defined for interactive manipulation
    through the GUI.  This should be done by setting the widgets in
    the layout.  I.e.::

        from .. import widgets as w

        class(Model):
            params = dict(n=1, b=2.0)
            layout = w.VBox([
                w.FloatLogSlider(name='cooling',
                                 base=10, min=-10, max=1, step=0.2,
                                 description='Cooling'),
                w.FloatSlider(name='V0_mu',
                              min=-2, max=2, step=0.1,
                              description='V0/mu'),
                w.density])

    """
    params = Attribute("Dictionary of parameters and default values.")
    layout = Attribute("Widget layout.")

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
