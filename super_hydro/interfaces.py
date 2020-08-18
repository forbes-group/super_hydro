"""Interfaces for various components of the system.
"""
from zope.interface import Interface, Attribute, implementer
from zope.interface.verify import verifyClass, verifyObject

__all__ = ['IModel', 'IServer',
           'implementer', 'verifyClass', 'verifyObject']


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
            param_doc = dict(n='Parameter n', b='Parameter b')
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
    params_doc = Attribute("Dictionary of parameter documentation.")
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

    def get(param):
        """Return the specified parameter.

        This is called interactively by the server.  Parameters could
        be implemented with properties, but our server explicitly
        calls this method to limit the require interface.
        """


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
           description of the command.

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

        Arguments
        ---------
        params : [str]
           List of parameters.

        Returns
        -------
        param_dict : {param: val}
           Dictionary of values corresponding to specified parameters.
        """

    def set(param_dict, client=None):
        """Set the specified quantities.

        Arguments
        ---------
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
