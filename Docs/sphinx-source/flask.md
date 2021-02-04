# super\_hydro Flask-based Web Client

## Flask Framework

The [Flask](https://flask.palletsprojects.com/en/1.1.x/) client framework 
(Flask) provides two primary functions: establish routing/rendering between
the User Frontend Web Client (Web Client) and Computational server (Server),
 and mediating interaction and display data between the two.

### Startup

The Flask module loads the configuration parameters, most notably the 
physics module containing intended simulation models (models). From this,
it pulls the names of all classes/models contained within and stores them.

It then begins hosting the Client on the designated host IP and Port number,
using the Flask `render_template()` function with `@app.route()` decorators
to manage HTTP routes to the landing page (index) or model page.

The model page routing is dynamically generated based on the chosen model,
which prevents the need for distinct routing for each model. Each model is
loaded into a template (`model.html`) HTML page and specified using Jinja2
variables.

Once the model page is loaded by a User, the Client requests startup information
for the relevant model. This triggers Flask to either start a new Server 
instance for the relevant physics model, or update the User count for the
currently running Server.

When the Server is running, Flask then queries all current parameters and
returns them to the model page for update and display.

The Flask startup then starts or connects the page to a pushing thread, which
continuously queries the Server for relevant display animation information
and passes it to the Client.

### Routing and Rendering

The communication is linked to the Client via web sockets managed through
[eventlet](https://pypi.org/project/eventlet/), which is handled 
implicitly through calls and methods from 
[Flask-SocketIO](https://flask-socketio.readthedocs.io/en/latest/).

All communication between the Client and Server is handled through Flask
using the Flask-SocketIO Namespace Class `Demonstration`. The internal 
methods receive Client data keyed to Client `emit` events with names 
matching the appropriate `on_` method name.

The Flask-SocketIO namespace (Demonstration) separates the models into 
internal `dict` keys, which contain all relevant information for the 
routing of a particular model: Model Name, User Count, Server.

Web socket communication between models is prevented by placing each into
their own Flask-SocketIO Room within the socket Namespace; by tying the
Room to the model class name, this allows generality and flexibility in
the Room creation.

### Communication

User interactions are read as inputs into Javscript and passed to Flask via 
the Javascript [socket.io](socket.io/docs/v3/index.html) API. This uses a 
static namespace and uses `emit()` to pass the Room name (model), the 
parameter/action being modified, and the new parameter value.

Flask recieves this information and passes it into appropriate Server calls,
emitting Server return information (as appropriate).

### HTML/JS User Interface

The User interface is displayed as HTML static pages generated from templates
using Jinja2.

Interaction sliders/toggles are created based on a nested list `sliders` that 
is required in each class method representing a physics model.

The remaining display area is filled by multiple HTML Canvas elements laid over
each other. The lowest layer displays the color map conversion of the model
density array. The top layer displays the finger potential current position
(white circle) which is connected to the User placed finger (black dot) by a
white line. These are both continuously updated by Flask's background thread
that continuously queries the Server for the needed information.

When another User changes a parameter value, this is passed to other users via
Flask and updated appropriately. This allows multiple Users to actively interact
with a single model and see the effects of other User inputs in real-time. 
