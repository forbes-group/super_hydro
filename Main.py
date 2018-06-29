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

#create a texture to draw the data on
Nxy = (32, 64)#This is (y,x)
ratio = Nxy[1]/Nxy[0]#window width = ratio * height
Window.size = (1000, 1000/ratio)#windows aspect ratio the same as the grid
texture = Texture.create(size = (Nxy[1],Nxy[0]), colorfmt='rgba')

healing_length = 0.1
dt_t_scale = 1.0
steps = 20
s = gpe.State(Nxy=Nxy, V0_mu=0.5, test_finger=False,
          healing_length=healing_length, dt_t_scale=dt_t_scale)

#For scaling data
Winx = Window.width
Winy = Window.height

class Display(FloatLayout):
    potential = 0
    angle = NumericProperty(0)
    arrow_size = ListProperty(0)
    arrow_visible = True
    event = None
    dt = 1.0/20.0

    def __init__(self, **kwargs):
        self.push_to_texture()
        self.angle = 45
        self.arrow_size = (0,0)
        self.event = Clock.schedule_interval(self.update, self.dt)
        self.event.cancel()#for pausing game when screens change
        super().__init__(**kwargs)

    def push_to_texture(self):
        ##viridis is the color map I need to display in
        s.step(steps)
        n = s.get_density()
        array = cm.viridis((n-n.min())/(n.max()-n.min()))
        array *= int(255/array.max())#normalize values
        data = array.astype(dtype = 'uint8')
        data = data.tobytes()

        #blit_buffer takes the data and put it onto my texture
        texture.blit_buffer(data,bufferfmt = 'ubyte', colorfmt = 'rgba')
        texture.flip_vertical()#kivy has y going up, not down

    def scroll_values(self, *args):
        s.V0_mu = args[1]

    def force_angle(self):#point the arrow towards the finger
        dist_x = self.ids.finger.pos[0] - self.ids.potential.pos[0]
        dist_y = self.ids.finger.pos[1] - self.ids.potential.pos[1]

        #dynamically scale the arrow
        if self.arrow_visible:
            self.arrow_size = (.4 * np.sqrt(dist_x**2 + dist_y**2),
                            .4 * np.sqrt(dist_x**2 + dist_y**2))
        else:
            self.arrow_size = 0,0

        if dist_x != 0:
            radians = np.arctan(dist_y / dist_x)
            if dist_x >= 0:
                self.angle = int(np.degrees(radians) - 45)
            else:
                self.angle = int(np.degrees(radians) + 135)
        else:
            self.angle = -45

    def on_checkbox_active(self,value):
        self.arrow_visible = value

    #for getting the texture into the kivy file
    def get_texture(self):
        return texture

    def no_collision(self,touch): #checks for button collision during game
        collision = True
        scroll = self.ids.my_slider
        home = self.ids.home_button

        if scroll.collide_point(touch.x,touch.y) != True and\
                home.collide_point(touch.x, touch.y) != True:
            collision = False
        return collision

    def on_touch_move(self,touch):
        if self.no_collision(touch) is False:
            s.set_xy0(-(touch.y - (Winy/2)) * (s.Lxy[0]/Winy),  # align touch with screen
                           (touch.x - (Winx/2)) * (s.Lxy[1]/Winx))
            finger = self.ids.finger
            potential = self.ids.potential
            force = self.ids.force

            if s.V0_mu >= 0:#adjust for V0 scroll bar
                Vpos = unravel_index(s.get_Vext().argmax(),
                                    s.get_Vext().shape)
            else:
                Vpos = unravel_index(s.get_Vext().argmin(),
                                s.get_Vext().shape)

            y = float(Winy - (Vpos[0]*Winy/Nxy[0]))
            x = float(Vpos[1]*Winx/Nxy[1])

            finger.pos = (touch.x-(Marker().size[0]/2),
                            touch.y-(Marker().size[1]/2))
            potential.pos = [x-(Marker().size[0]/2),y-(Marker().size[1]/2)]
            #if arrow_visible:
            force.pos = [x,y]
            self.force_angle()



    def update(self, dt):
        potential = self.ids.potential
        force = self.ids.force

        if s.V0_mu >= 0:#pot marker always goes to finger
            Vpos = unravel_index(s.get_Vext().argmax(),
                                s.get_Vext().shape)
        else:
            Vpos = unravel_index(s.get_Vext().argmin(),
                            s.get_Vext().shape)

        y = float(Winy - (Vpos[0]*Winy/Nxy[0]))
        x = float(Vpos[1]*Winx/Nxy[1])
        potential.pos = [x -(Marker().size[0]/2),
                        y -(Marker().size[1]/2)]
        force.pos = [x,y]
        self.force_angle()
        self.push_to_texture()
        self.canvas.ask_update()


class StartScreen(Screen):
    #allows changing of game variables

    def __init__(self, **kwargs):
        #self.ids.arrow_check.active = True
        super().__init__(**kwargs)

    def V0_values(self, *args):
        s.V0_mu = args[1]

    def cooling_values(self,*args):
        s.cooling_phase = complex(1,10**int(args[1]))
        self.ids.cooling_val.text = str(s.cooling_phase)

    def Nxy_values(self, *args):#changes the values, but breaks the program
        s.Nxy = 2**(args[1])

    def reset_game(self):
        s.n0 = s.hbar**2/2.0/s.healing_length**2/s.g
        s.mu = s.g*s.n0
        s.mu_min = max(0, min(s.mu, s.mu*(1-s.V0_mu)))
        s.c_s = np.sqrt(s.mu/s.m)
        s.c_min = np.sqrt(s.mu_min/s.m)
        s.v_max = 1.1*s.c_min
        s.data = np.ones(s.Nxy, dtype=complex) * np.sqrt(s.n0)
        s._N = s.get_density().sum()

        s.z_finger = 0 + 0j
        s.pot_k_m = 10.0
        s.pot_z = 0 + 0j
        s.pot_v = 0 + 0j
        s.pot_damp = 4.0

        s.t = -10000
        s._phase = -1.0/s.hbar
        s.step(100)
        s.t = 0
        s._phase = -1j/s.hbar/s.cooling_phase
        s.c_s = np.sqrt(s.mu/s.m)
        s.c_min = np.sqrt(s.g*s.get_density().min()/s.m)
        s.v_max = 0.8*s.c_min

class ScreenMng(ScreenManager):#manages all the screens
    def __init__(self,**kwargs):
        super().__init__(**kwargs)

class Arrow(Widget):
    pass#class for displaying a vector between the markers

class Marker(Widget):
    #class for displaying finger and potential markers
    #all done in the .kv file
    pass

class SuperHydroApp(App):
    Title = 'Super Hydro'

    def build(self):
        return ScreenMng()


if __name__ == "__main__":
    SuperHydroApp().run()
