import os
import sys

import numpy as np

from .. import config, communication, utils

_LOGGER = utils.Logger(__name__)
log = _LOGGER.log
log_task = _LOGGER.log_task

######################################################################
# We grab the options here because kivy will otherwise destroy all the
# command-line options.
# https://groups.google.com/d/msg/kivy-users/gLBRrqRp7MI/I18pjq80ymkJ
def get_opts():
    """Get the client configuration options."""
    with log_task("Reading configuration"):
        parser = config.get_client_parser()
        opts, other_args = parser.parse_known_args()
        log("Unused Options: {}".format(other_args), 100)
    return opts

_OPTS = get_opts()

from kivy.config import Config
Config.set('graphics', 'resizable', False)
from kivy.app import App
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.properties import NumericProperty, ListProperty, ObjectProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.accordion import Accordion, AccordionItem
from kivy.clock import Clock




class Display(FloatLayout):
    """Main simulation layout."""
    angle = NumericProperty(0)
    arrow_size = ListProperty(0)
    arrow_visible = True
    event = None
    Nx, Ny = 0,0

    number_keys_pressed = 0
    keys_pressed = {
        'w':False,
        's':False,
        'a':False,
        'd':False
    }

    texture = None

    def __init__(self, **kwargs):
        app = App.get_running_app()
        self.comm = app.comm
        self.opts = app.opts
        self.graph_pxsize = app.graph_pxsize
        
        self.Nx, self.Ny = self.comm.get(b"Nxy")
        self.get_texture()
            
        with log_task("Get density from server and push to texture"):
            self.push_to_texture()
            
        self.angle = 45
        self.arrow_size = (0, 0)
        print("fps: {}".format(1./self.opts.fps))
        self.event = Clock.schedule_interval(self.update, 1./self.opts.fps)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self.event.cancel()  # for pausing game when screens change
        super().__init__(**kwargs)

    # for getting the texture into the kivy file
    def get_texture(self):
        if self.texture is None:
            with log_task("Creating texture"):
                self.texture = Texture.create(size=(self.Nx, self.Ny),
                                              colorfmt='rgba')
        return self.texture

    def push_to_texture(self):
        data = self.comm.get_array(b"Frame").tobytes()
        # blit_buffer takes the data and put it onto my texture
        self.get_texture().blit_buffer(data, bufferfmt='ubyte',
                                       colorfmt='rgba')

    def get_graph_pxsize(self):
        return self.graph_pxsize

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        finger = self.ids.finger
        framex = Window.size[0] - self.graph_pxsize
        framey = Window.size[1] - self.graph_pxsize

        pressed_key = keycode[1]

        if pressed_key == 'w':
            finger.pos = finger.pos[0], finger.pos[1] + 20
        if pressed_key == 's':
            finger.pos = finger.pos[0], finger.pos[1] - 20
        if pressed_key == 'd':
            finger.pos = finger.pos[0] + 20, finger.pos[1]
        if pressed_key == 'a':
            finger.pos = finger.pos[0] - 20, finger.pos[1]

        touch_input = [finger.pos[0] + Marker().size[0]/2,
                        finger.pos[1] + Marker().size[1]/2 - self.graph_pxsize]

        #keeps input within game border
        if touch_input[0] > framex:
            touch_input[0] = 0
            finger.pos[0] = 0
        elif touch_input[0] <= 0:
            touch_input[0] = framex - 20
            finger.pos[0] = framex - 20
        if touch_input[1] > framey:
            touch_input[1] = 0
            finger.pos[1] = 0 + self.graph_pxsize
        elif touch_input[1] <= 0:
            touch_input[1] = framey - 20
            finger.pos[1] = framey + self.graph_pxsize - 20

        # Normalize to frame
        touch_input[0] = touch_input[0]/framex
        touch_input[1] = touch_input[1]/framey
        self.comm.send(b"OnTouch", touch_input)

    def _on_keyboard_up(self,keycode):
        up_key = keycode[1]
        self.keys_pressed[up_key] = False

    def force_angle(self):      # point the arrow towards the finger
        dist_x = self.ids.finger.pos[0] - self.ids.potential.pos[0]
        dist_y = self.ids.finger.pos[1] - self.ids.potential.pos[1]

        # dynamically scale the arrow
        if self.arrow_visible:
            self.arrow_size = (.4 * np.sqrt(dist_x**2 + dist_y**2),
                               .4 * np.sqrt(dist_x**2 + dist_y**2))
        else:
            self.arrow_size = (0, 0)

        radians = np.arctan2(dist_y, dist_x)

        # Rotate by -45deg here because the png for the arrow points
        # to the upper right.
        self.angle = int(np.degrees(radians) - 45)

    def on_checkbox_active(self, value):
        self.arrow_visible = value

    def no_collision(self, touch):  # checks for button collision during game
        collision = True
        #scroll = self.ids.my_slider
        pause = self.ids.pause_button

        """within game space/not touching pause button"""
        if (not pause.collide_point(touch.x, touch.y) and
            (touch.x < Window.size[0] - self.graph_pxsize and
                touch.y > self.graph_pxsize)):
            collision = False
        return collision

    def get_Vpos(self):
        Winx = Window.size[0] - self.graph_pxsize
        Winy = Window.size[1] - self.graph_pxsize
        potential = self.ids.potential
        force = self.ids.force

        Vpos = np.array(self.comm.get(b"Vpos"))
        Vx, Vy = Vpos[0], Vpos[1]

        x = float(Vx*Winx/self.Nx)
        y = float(Vy*Winy/self.Ny)
        potential.pos = [x - (Marker().size[0]/2),
                         y - (Marker().size[1]/2) + self.graph_pxsize]
        force.pos = [x, y + self.graph_pxsize]
        self.force_angle()


    """This allows single clicks to change Vpos, but
            prevents other widgets on screen from being used"""
    #def on_touch_down(self, touch):
    #    if self.no_collision(touch) is False:
    #        self.on_touch_move(touch)

    def on_touch_move(self, touch):
        finger = self.ids.finger

        if self.no_collision(touch) is False:
            #adjusts for the border size
            touch_input = [touch.x, touch.y - self.graph_pxsize]

            # Normalize to frame size
            framex = Window.size[0] - self.graph_pxsize
            framey = Window.size[1] - self.graph_pxsize

            touch_input[0] /= framex
            touch_input[1] /= framey
            
            self.comm.send(b"OnTouch", touch_input)

            self.get_Vpos()

            finger.pos = (touch.x-(Marker().size[0]/2),
                          touch.y-(Marker().size[1]/2))

    def update(self, dt):
        self.get_Vpos()
        self.push_to_texture()
        self.canvas.ask_update()


class StartScreen(Screen):
    """Initial start screen with menu choices etc."""
    # allows changing of game variables

    def __init__(self, **kwargs):
        app = App.get_running_app()
        self.comm = app.comm
        super().__init__(**kwargs)

    def V0_values(self, *args):
        self.comm.send(b"V0", args[1])

    def cooling_values(self, *args):
        self.ids.cooling_val.text = str(complex(1, 10**int(args[1])))
        self.comm.send(b"Cooling", args[1])

    def reset_game(self):
        self.comm.request(b"Reset")

class ScreenMng(ScreenManager):
    """Manages all of the screens (i.e. which screen is visible etc.)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Arrow(Widget):
    """Widget to display a vector between the markers."""
    pass


class Marker(Widget):
    """Widget for displaying finger and potential markers."""
    pass


class SuperHydroApp(App):
    Title = 'Super Hydro'

    def __init__(self, opts):
        self.opts = opts
        App.__init__(self)

    def build(self):
        global Window
        with log_task("Connecting to server"):        
            self.comm = communication.Client(opts=self.opts)

        self.graph_pxsize = 150

        Nx, Ny = self.comm.get(b"Nxy")
        frame_width = self.opts.window_width
        frame_height = self.opts.window_width * Ny/Nx
        window_width = frame_width + self.graph_pxsize
        window_height = frame_height + self.graph_pxsize

        Window.size = (window_width, window_height)
        log("window: {}".format(Window.size))
        return ScreenMng()


def run():
    SuperHydroApp(opts=_OPTS).run()
