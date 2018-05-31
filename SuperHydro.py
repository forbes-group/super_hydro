import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm

import numpy as np
from numpy import unravel_index
import gpe
import time

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.properties import ObjectProperty, NumericProperty, ListProperty
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.slider import Slider
from kivy.clock import Clock

#create a texture to draw the data on
Nxy = (32, 64)#This is (y,x)
ratio = Nxy[1]/Nxy[0]#window width = ratio * height
Window.size = (1000,1000/ratio)#windows aspect ratio the same as the grid
texture = Texture.create(size = (Nxy[1],Nxy[0]), colorfmt='rgba')

healing_length = 0.1
dt_t_scale = 1.0
steps = 20

#For scaling data
Winx = Window.width
Winy = Window.height

class Arrow(Widget):
    pass#class for displaying a vector between the markers

class Marker(Widget):
    #class for displaying finger and potential markers
    #all done in the .kv file
    pass

class Display(FloatLayout):
    potential = 0
    angle = NumericProperty(0)
    arrow_size = ListProperty(0)

    s = gpe.State(Nxy=Nxy, V0_mu=0.5, test_finger=False,
                  healing_length=healing_length, dt_t_scale=dt_t_scale)

    def __init__(self, **kwargs):
        self.push_to_texture()
        self.angle = 45
        self.arrow_size = (0,0)
        super().__init__(**kwargs)

    def push_to_texture(self):
        ##viridis is the color map I need to display in
        self.s.step(steps)
        n = self.s.get_density()
        #array = cm.viridis((n/self.s.n0))#((n-n.min())/(n.max()-n.min()))
        array = cm.viridis((n-n.min())/(n.max()-n.min()))
        array *= int(255/array.max())#normalize values
        data = array.astype(dtype = 'uint8')
        data = data.tobytes()

        #blit_buffer takes the data and put it onto my texture
        texture.blit_buffer(data,bufferfmt = 'ubyte', colorfmt = 'rgba')
        texture.flip_vertical()#kivy has y going up, not down

    def scroll_values(self, *args):
        self.s.V0_mu = args[1]

    def force_angle(self):#point the arrow towards the finger
        dist_x = self.ids.finger.pos[0] - self.ids.potential.pos[0]
        dist_y = self.ids.finger.pos[1] - self.ids.potential.pos[1]

        #dynamically scale the arrow
        self.arrow_size = (.4 * np.sqrt(dist_x**2 + dist_y**2),
                            .4 * np.sqrt(dist_x**2 + dist_y**2))

        if dist_x != 0:
            radians = np.arctan(dist_y / dist_x)
            if dist_x >= 0:
                self.angle = int(np.degrees(radians) - 45)
            else:
                self.angle = int(np.degrees(radians) + 135)
        else:
            self.angle = -45


    #for getting the texture into the kivy file
    def get_texture(self):
        return texture

    def on_touch_move(self,touch):
        self.s.set_xy0(-(touch.y - (Winy/2)) * (self.s.Lxy[0]/Winy),  # align touch with screen
                       (touch.x - (Winx/2)) * (self.s.Lxy[1]/Winx))
        finger = self.ids.finger
        potential = self.ids.potential
        force = self.ids.force

        if self.s.V0_mu >= 0:#adjust for V0 scroll bar
            Vpos = unravel_index(self.s.get_Vext().argmax(),
                                self.s.get_Vext().shape)
        else:
            Vpos = unravel_index(self.s.get_Vext().argmin(),
                            self.s.get_Vext().shape)

        y = float(Winy - (Vpos[0]*Winy/Nxy[0]))
        x = float(Vpos[1]*Winx/Nxy[1])

        finger.pos = (touch.x-(Marker().size[0]/2),
                        touch.y-(Marker().size[1]/2))
        potential.pos = [x-(Marker().size[0]/2),y-(Marker().size[1]/2)]
        force.pos = [x,y]
        self.force_angle()

    def update(self, dt):
        potential = self.ids.potential
        force = self.ids.force

        if self.s.V0_mu >= 0:#pot marker always goes to finger
            Vpos = unravel_index(self.s.get_Vext().argmax(),
                                self.s.get_Vext().shape)
        else:
            Vpos = unravel_index(self.s.get_Vext().argmin(),
                            self.s.get_Vext().shape)

        y = float(Winy - (Vpos[0]*Winy/Nxy[0]))
        x = float(Vpos[1]*Winx/Nxy[1])
        potential.pos = [x -(Marker().size[0]/2),
                        y -(Marker().size[1]/2)]
        force.pos = [x,y]
        self.force_angle()
        self.push_to_texture()
        self.canvas.ask_update()

class SuperHydroApp(App):
    Title = 'Super Hydro'

    def build(self):
        display = Display()
        Clock.schedule_interval(display.update,1.0/20.0)
        return display

if __name__ == "__main__":
    SuperHydroApp().run()
