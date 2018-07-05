import sys

import attr

import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm

import numpy as np
from numpy import unravel_index
import gpe

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock


@attr.s
class Parameters(object):
    Nx = attr.ib(default=128//2)
    Ny = attr.ib(default=64//2)
    window_width = attr.ib(default=1000)
    healing_length = attr.ib(default=0.1)
    dt_t_scale = attr.ib(default=1.0)
    steps = attr.ib(default=20)

    @property
    def window_size(self):
        return (self.window_width, self.window_width*self.Ny/self.Nx)

#Nxy = (64//2, 128//2)#This is (y,x)
#ratio = Nxy[1]/Nxy[0]#window width = ratio * height
#Window.size = (1000, 1000/ratio)#windows aspect ratio the same as the grid
#create a texture to draw the data on
#texture = Texture.create(size = (Nxy[1],Nxy[0]), colorfmt='rgba')

#For scaling data
Winx = Window.width
Winy = Window.height


class Display(FloatLayout):
    """Main simulation layout."""
    potential = 0
    angle = NumericProperty(0)
    arrow_size = ListProperty(0)
    arrow_visible = True
    event = None
    dt = 1.0/20.0

    texture = None

    def __init__(self, **kwargs):
        self.push_to_texture()
        self.angle = 45
        self.arrow_size = (0, 0)
        self.event = Clock.schedule_interval(self.update, self.dt)
        self.event.cancel()  # for pausing game when screens change
        super().__init__(**kwargs)

    def push_to_texture(self):
        ## viridis is the color map I need to display in
        app = App.get_running_app()
        state = app.state
        state.step(app.params.steps)
        n = state.get_density()
        array = cm.viridis((n-n.min())/(n.max()-n.min()))
        array *= int(255/array.max())  # normalize values
        data = array.astype(dtype='uint8')
        data = data.tobytes()

        # blit_buffer takes the data and put it onto my texture
        self.get_texture().blit_buffer(data, bufferfmt='ubyte',
                                       colorfmt='rgba')
        self.get_texture().flip_vertical()  # kivy has y going up, not down

    def scroll_values(self, *args):
        app = App.get_running_app()
        app.state.V0_mu = args[1]

    def force_angle(self):      # point the arrow towards the finger
        dist_x = self.ids.finger.pos[0] - self.ids.potential.pos[0]
        dist_y = self.ids.finger.pos[1] - self.ids.potential.pos[1]

        # dynamically scale the arrow
        if self.arrow_visible:
            self.arrow_size = (.4 * np.sqrt(dist_x**2 + dist_y**2),
                               .4 * np.sqrt(dist_x**2 + dist_y**2))
        else:
            self.arrow_size = (0, 0)

        if dist_x != 0:
            radians = np.arctan(dist_y / dist_x)
            if dist_x >= 0:
                self.angle = int(np.degrees(radians) - 45)
            else:
                self.angle = int(np.degrees(radians) + 135)
        else:
            self.angle = -45

    def on_checkbox_active(self, value):
        self.arrow_visible = value

    # for getting the texture into the kivy file
    def get_texture(self):
        app = App.get_running_app()
        params = app.params
        if self.texture is None:
            self.texture = Texture.create(size=(params.Nx, params.Ny),
                                          colorfmt='rgba')
        return self.texture

    def no_collision(self, touch):  # checks for button collision during game
        collision = True
        scroll = self.ids.my_slider
        home = self.ids.home_button

        if (not scroll.collide_point(touch.x, touch.y) and
                not home.collide_point(touch.x, touch.y)):
            collision = False
        return collision

    def on_touch_move(self, touch):
        app = App.get_running_app()
        state = app.state
        if self.no_collision(touch) is False:
            # align touch with screen
            state.set_xy0(-(touch.y - (Winy/2)) * (state.Lxy[0]/Winy),
                           (touch.x - (Winx/2)) * (state.Lxy[1]/Winx))
            finger = self.ids.finger
            potential = self.ids.potential
            force = self.ids.force

            # adjust for V0 scroll bar
            if state.V0_mu >= 0:
                Vpos = unravel_index(state.get_Vext().argmax(),
                                     state.get_Vext().shape)
            else:
                Vpos = unravel_index(state.get_Vext().argmin(),
                                     state.get_Vext().shape)

            app = App.get_running_app()
            Nxy = (app.params.Ny, app.params.Nx)
            y = float(Winy - (Vpos[0]*Winy/Nxy[0]))
            x = float(Vpos[1]*Winx/Nxy[1])

            finger.pos = (touch.x-(Marker().size[0]/2),
                          touch.y-(Marker().size[1]/2))
            potential.pos = [x-(Marker().size[0]/2),
                             y-(Marker().size[1]/2)]
            # if arrow_visible:
            force.pos = [x, y]
            self.force_angle()

    def update(self, dt):
        app = App.get_running_app()
        state = app.state
        potential = self.ids.potential
        force = self.ids.force

        # pot marker always goes to finger
        if state.V0_mu >= 0:
            Vpos = unravel_index(state.get_Vext().argmax(),
                                 state.get_Vext().shape)
        else:
            Vpos = unravel_index(state.get_Vext().argmin(),
                                 state.get_Vext().shape)

        app = App.get_running_app()
        Nxy = (app.params.Ny, app.params.Nx)
        y = float(Winy - (Vpos[0]*Winy/Nxy[0]))
        x = float(Vpos[1]*Winx/Nxy[1])
        potential.pos = [x - (Marker().size[0]/2),
                         y - (Marker().size[1]/2)]
        force.pos = [x, y]
        self.force_angle()
        self.push_to_texture()
        self.canvas.ask_update()


class StartScreen(Screen):
    """Initial start screen with menu choices etc."""
    # allows changing of game variables

    def __init__(self, **kwargs):
        # self.ids.arrow_check.active = True
        super().__init__(**kwargs)

    def V0_values(self, *args):
        app = App.get_running_app()
        app.state.V0_mu = args[1]

    def cooling_values(self, *args):
        app = App.get_running_app()
        state = app.state
        state.cooling_phase = complex(1, 10**int(args[1]))
        self.ids.cooling_val.text = str(state.cooling_phase)

    def Nxy_values(self, *args):
        """Called by Kivy to change resoluton on start screen."""
        app = App.get_running_app()
        app.params.Ny, app.params.Nx = 2**args[1], 2**args[1]
        self.reset_game()

    def reset_game(self):
        app = App.get_running_app()
        app.state = gpe.State(Nxy=(params.Ny, params.Nx),
                              V0_mu=0.5, test_finger=False,
                              healing_length=params.healing_length,
                              dt_t_scale=params.dt_t_scale)


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
        self.params = kw.pop('params')
        self.state = gpe.State(Nxy=(params.Ny, params.Nx),
                               V0_mu=0.5, test_finger=False,
                               healing_length=params.healing_length,
                               dt_t_scale=params.dt_t_scale)
        App.__init__(self, *v, **kw)

    def build(self):
        return ScreenMng()


if __name__ == "__main__":
    # Look at argparse
    # And config file
    if len(sys.argv) == 3:
        Nx, Ny = int(sys.argv[1]), int(sys.argv[2])

    params = Parameters()
    Window.size = params.window_size  # windows aspect ratio same as grid
    SuperHydroApp(params=params).run()
