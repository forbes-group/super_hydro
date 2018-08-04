import sys
import socket
import attr
import json

import numpy as np

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
    dt = 1.0/20.0
    Nx, Ny = 0,0

    texture = None

    def __init__(self, **kwargs):
        self.get_texture()
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
            sock.send("Texture".encode())
            Nxy = sock.recv(128).decode()
            N = json.loads(Nxy)
            self.Nx, self.Ny = int(N[0]), int(N[1])
            self.texture = Texture.create(size=(self.Nx, self.Ny),
                                            colorfmt='rgba')
        return self.texture

    def push_to_texture(self):
        sock.send("Density".encode())
        arr_length = self.Nx * self.Ny * 4
        deserialize = json.loads(sock.recv(65536).decode())
        Density_data = np.array(deserialize)

        data = Density_data.astype(dtype='uint8')
        data = data.tobytes()
        # blit_buffer takes the data and put it onto my texture
        self.get_texture().blit_buffer(data, bufferfmt='ubyte',
                                       colorfmt='rgba')

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        finger = self.ids.finger

        if keycode[1] == 'd':
            finger.pos[0] += 25
        elif keycode[1] == 'a':
            finger.pos[0] -= 25
        elif keycode[1] == 'w':
            finger.pos[1] += 25
        elif keycode[1] == 's':
            finger.pos[1] -= 25

        touch_input = [finger.pos[0] + Marker().size[0]/2,
                        finger.pos[1] + Marker().size[1]/2]

        if touch_input[0] > Window.size[0]:
            touch_input[0] = 0
            finger.pos[0] = 0
        elif touch_input[0] <= 0:
            touch_input[0] = Window.size[0] - 20
            finger.pos[0] = Window.size[0] - 20
        if touch_input[1] > Window.size[1]:
            touch_input[1] = 0
            finger.pos[1] = 0
        elif touch_input[1] <= 0:
            touch_input[1] = Window.size[1] - 20
            finger.pos[1] = Window.size[1] - 20

        send_data = "OnTouch"
        send_data += json.dumps(touch_input)
        sock.send(send_data.encode())
        error_check = sock. recv(128).decode()
        if error_check == "ERROR":
            print("Touch update unsuccessful")

        self.get_Vpos()
        #self.update(2)

    def scroll_values(self, *args):
        pass
        #app = App.get_running_app()
        #app.state.V0_mu = args[1]

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
        home = self.ids.pause_button

        #if (not scroll.collide_point(touch.x, touch.y) and
        #        not home.collide_point(touch.x, touch.y)):
        if not home.collide_point(touch.x,touch.y):
            collision = False
        return collision

    def get_Vpos(self):
        Winx = Window.size[0]
        Winy = Window.size[1]
        potential = self.ids.potential
        force = self.ids.force

        sock.send("Vpos".encode())
        error_check = sock.recv(128).decode()

        if error_check == "ERROR":
            print("V0 change unsuccessful")
        else:
            deserialize = json.loads(error_check)
            Vpos = np.array(deserialize)
            Vx, Vy = Vpos[0], Vpos[1]

            x = float(Vx*Winx/self.Nx)
            y = float(Vy*Winy/self.Ny)
            potential.pos = [x - (Marker().size[0]/2),
                             y - (Marker().size[1]/2)]
            force.pos = [x, y]
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
            send_data += json.dumps([touch.x, touch.y])

            sock.send(send_data.encode())
            error_check = sock.recv(128).decode()
            if error_check == "ERROR":
                print("Touch update unsuccessful")

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
        sock.send(send_data.encode())
        error_check = sock.recv(128).decode()
        if error_check == "ERROR":
            print("V0 change unsuccessful")

    def cooling_values(self, *args):
        self.ids.cooling_val.text = str(complex(1,10**int(args[1])))
        send_data = "Cooling"
        send_data += str(int(args[1]))
        sock.send(send_data.encode())
        error_check = sock.recv(128).decode()
        if error_check == "ERROR":
            print("Cooling change unsuccessful")

    def reset_game(self):
        sock.send("Reset".encode())
        error_check = sock.recv(128).decode()
        if error_check == "ERROR":
            print("Game reset unsuccessful")

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
    host = '127.0.0.1'
    port = 8888
    sock = socket.socket()
    sock.connect((host,port))

    # Look at argparse
    # And config file
    if len(sys.argv) == 3:
        Nx, Ny = int(sys.argv[1]), int(sys.argv[2])
    else:
        # windows aspect ratio same as grid
        win = sock.recv(128).decode()
        window = json.loads(win)
        Window.size = int(window[0]), int(window[1])
        print ("window:",Window.size)
    SuperHydroApp().run()
