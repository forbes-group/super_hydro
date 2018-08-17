import configparser
from contextlib import contextmanager
import json
import logging
import socket
import sys

import attr
import numpy as np

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

from communication import Communicator


def log(msg, level=logging.ERROR):
    """Log msg to the logger."""
    # Get logger each time so handlers are properly dealt with
    logging.getLogger(__name__).log(level=level, msg=msg)
    

@contextmanager
def log_task(msg, _level=[0]):
    indent = " " * 2 * _level[0]
    msg = indent + msg
    log(msg + "...")
    try:
        _level[0] += 1
        yield
        log(msg + ". Done.")
    except:
        log(msg + ". Failed!", level=logging.ERROR)
        raise
    finally:
        _level[0] -= 1


class Display(FloatLayout):
    """Main simulation layout."""
    angle = NumericProperty(0)
    arrow_size = ListProperty(0)
    arrow_visible = True
    event = None
    dt = 1.0/20.0
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
        with log_task("Getting texture from server"):
            self.get_texture()
            
        with log_task("Get density from server and push to texture"):
            self.push_to_texture()
            
        self.angle = 45
        self.arrow_size = (0, 0)
        self.event = Clock.schedule_interval(self.update, self.dt)
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        self.event.cancel()  # for pausing game when screens change
        super().__init__(**kwargs)

    # for getting the texture into the kivy file
    def get_texture(self):
        if self.texture is None:
            communicator.send("Texture")
            N = communicator.get_json(128)
            self.Nx, self.Ny = int(N[0]), int(N[1])
            self.texture = Texture.create(size=(self.Nx, self.Ny),
                                            colorfmt='rgba')
        return self.texture

    def push_to_texture(self):
        communicator.send("Density")
        #arr_length = self.Nx * self.Ny * 4
        deserialize = communicator.get_json(65536)
        Density_data = np.array(deserialize)

        data = Density_data.astype(dtype='uint8')
        data = data.tobytes()
        # blit_buffer takes the data and put it onto my texture
        self.get_texture().blit_buffer(data, bufferfmt='ubyte',
                                       colorfmt='rgba')

    def get_graph_pxsize(self):
        return graph_pxsize

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        finger = self.ids.finger
        winx = Window.size[0] - graph_pxsize
        winy = Window.size[1] - graph_pxsize

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
                        finger.pos[1] + Marker().size[1]/2 - graph_pxsize]

        #keeps input within game border
        if touch_input[0] > winx:
            touch_input[0] = 0
            finger.pos[0] = 0
        elif touch_input[0] <= 0:
            touch_input[0] = winx - 20
            finger.pos[0] = winx - 20
        if touch_input[1] > winy:
            touch_input[1] = 0
            finger.pos[1] = 0 + graph_pxsize
        elif touch_input[1] <= 0:
            touch_input[1] = winy - 20
            finger.pos[1] = winy + graph_pxsize - 20

        send_data = "OnTouch"
        send_data += json.dumps(touch_input)
        communicator.request(send_data, "Keyboard update unsuccessful")

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
        if (not pause.collide_point(touch.x,touch.y) and
            (touch.x < Window.size[0] - graph_pxsize and
                touch.y > graph_pxsize)):
            collision = False
        return collision

    def get_Vpos(self):
        Winx = Window.size[0] - graph_pxsize
        Winy = Window.size[1] - graph_pxsize
        potential = self.ids.potential
        force = self.ids.force

        if communicator.request("Vpos", "V0 change unsuccessful"):
            deserialize = json.loads(error_check)
            Vpos = np.array(deserialize)
            Vx, Vy = Vpos[0], Vpos[1]

            x = float(Vx*Winx/self.Nx)
            y = float(Vy*Winy/self.Ny)
            potential.pos = [x - (Marker().size[0]/2),
                             y - (Marker().size[1]/2) + graph_pxsize]
            force.pos = [x, y + graph_pxsize]
            self.force_angle()


    """This allows single clicks to change Vpos, but
            prevents other widgets on screen from being used"""
    #def on_touch_down(self, touch):
    #    if self.no_collision(touch) is False:
    #        self.on_touch_move(touch)

    def on_touch_move(self, touch):
        finger = self.ids.finger

        if self.no_collision(touch) is False:
            send_data = "OnTouch"
            #adjusts for the border size
            send_data += json.dumps([touch.x, touch.y - graph_pxsize])

            communicator.send(send_data, "Touch update unsuccessful")

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
        super().__init__(**kwargs)

    def V0_values(self, *args):
        send_data = "V0"
        send_data += json.dumps(float(args[1]))
        communicator.request(send_data, "V0 change unsuccessful")

    def cooling_values(self, *args):
        self.ids.cooling_val.text = str(complex(1,10**int(args[1])))
        send_data = "Cooling"
        send_data += str(int(args[1]))
        communicator.request(send_data, "Cooling change unsuccessful")

    def reset_game(self):
        communicator.request("Reset", "Game reset unsuccessful")

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

    def __init__(self, *v,  **kw):
        App.__init__(self, *v, **kw)

    def build(self):
        return ScreenMng()


if __name__ == "__main__":
    with log_task("Reading configuration"):
        config = configparser.ConfigParser()
        config.read('config.ini')

    with log_task("Connecting to server"):        
        port = int(config['ui']['port'])    
        host = '127.0.0.1'

        communicator = Communicator(host=host, port=port)
        
    graph_pxsize = 150

    # Look at argparse
    # And config file
    # windows aspect ratio same as grid
    window = communicator.get_json(128)
    Window.size = int(window[0]) + graph_pxsize,\
                  int(window[1]) + graph_pxsize
    print ("window:",Window.size)
    SuperHydroApp().run()
