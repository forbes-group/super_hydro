"""Interfaces for various components of the system.
"""
from zope.interface import Interface, Attribute, implementer, implementedBy
from zope.interface.verify import verifyClass, verifyObject

__all__ = [
    "IModel",
    "IServer",
    "implementer",
    "implementedBy",
    "verifyClass",
    "verifyObject",
]


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

        class Model:
            params = dict(n=1, b=2.0)
            param_docs = dict(n='Parameter n', b='Parameter b')
            layout = w.VBox([
                w.FloatLogSlider(name='cooling',
                                 base=10, min=-10, max=1, step=0.2,
                                 description='Cooling'),
                w.FloatSlider(name='V0_mu',
                              min=-2, max=2, step=0.1,
                              description='V0/mu'),
                w.density])

    """

    params = Attribute(
        """Dictionary of parameters and default values.

        Must contain at least `Nx` and `Ny`, the grid dimensions."""
    )
    param_docs = Attribute("Dictionary of parameter documentation.")
    layout = Attribute("Widget layout.")

    def __init__(opts):
        """Constructor.

        Parameters
        ----------
        opts : Options
           Options object with attributes defined through the configuration mechanism.
           May contain updated values for `Nx` and `Ny`
        """

    def get_density():
        """Return the density array."""

    def get_trace_particles():
        """Return the list of tracer particle positions."""

    def get(param):
        """Return the specified parameter.

        This is called interactively by the server.  Parameters could
        be implemented with properties, but our server explicitly
        calls this method to limit the required interface.
        """

    def set(param, value):
        """Set the specified parameter.

        This is called interactively by the server.  Parameters could
        be implemented with properties, but our server explicitly
        calls this method to limit the require interface.
        """

    def step(N, tracer_particles):
        """Step the simulation N steps.

        Tracer particles will be removed in the future.
        """

    def get_params_and_docs():
        """Return a list of `(param, default, doc)` values for all parameters.

        This must be a class-method, and return all configurable values."""


class IServer(Interface):
    """Interface for the server.

    This interface defines the communication interface which the
    client will use to communicate with the server.  The methods here
    provide a direct way of interacting with the server using python,
    but an alternative implementation in super_hydro.communication
    abstracts this to the network.
    """

    def get_available_commands(client=None):
        """Return a dictionary of available commands.

        Returns
        -------
        available_commands : dict
           Dictionary of available commands.  Each is a dictionary
           whose key is the command name, and the value is a
           description of the command::

             {'do': {},         # Actions.
              'get': {},        # Parameters that can be fetched.
              'set': {},        # Parameters that can be set.
              'get_array': {},  # Arrays that can be fetched.
             }

        """

    def do(action, client=None):
        """Tell the server to perform the specified `action`."""

    def get(params, client=None):
        """Return the specified quantities.

        Parameters
        ----------
        params : [str]
           List of parameters.

        Returns
        -------
        param_dict : {param: val}
           Dictionary of values corresponding to specified parameters.
        """

    def set(param_dict, client=None):
        """Set the specified quantities.

        Parameters
        ----------
        param_dict : {param: val}
           Dictionary of values corresponding to specified
           parameters.  Unknown parameters should have a values of
           `NotImplemented`.  (This is encoded as the string
           `'_NotImplemented'` so values should not have this value.
        """

    def get_array(param, client=None):
        """Return the specified array."""

    def reset(client=None):
        """Reset server and return default parameters.

        Returns
        -------
        param_vals : {param: val}
           Dictionary of values corresponding to default parameters.
        """

    def quit(client=None):
        """Quit the server."""


class IConfiguration(Interface):
    """Public interface of the configuration object."""

    models = Attribute("Dictionary of Models (providing the IModel interface)")

    def get_options(Model):
        """Return a full option dictionary for the specified model.

        Arguments
        ---------
        Model : IModel or str
            Class or fully qualified import name for a class implementing the IModel
            interface.
        """

    def model_name(Model):
        """Return the canonical model name (the key in self.models)

        Arguments
        ---------
        Model : IModel or str
            Class or fully qualified import name for a class implementing the IModel
            interface.
        """
