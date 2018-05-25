import matplotlib
import matplotlib.pyplot as plt
from matplotlib import cm

import numpy as np
import gpe
print (gpe.__file__)
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.uix.slider import Slider

#create a texture to draw the data on
Nxy = (32,32)
texture = Texture.create(size = Nxy, colorfmt='rgba')

#create function data arrays
Lx = Window.width
Ly = Window.height
x = np.linspace(-8,8,Lx)
y = np.linspace(-6,6,Ly)
Ux = np.linspace(-8,8,Lx)
Uy = np.linspace(-6,6,Ly)
X,Y = np.meshgrid(x,y)
UX,UY = np.meshgrid(Ux,Uy)
x0 =-2
y0 = 2
sigma = 2.0

class Display(FloatLayout):
    potential = 0
    s = gpe.State(Nxy=Nxy)

    def __init__(self, **kwargs):
        self.push_to_texture()
        super().__init__(**kwargs)

    def f(self,X,Y):
        return np.exp(-((X -x0)**2 + (Y-y0)**2)/sigma**2) + self.potential

    def push_to_texture(self):
        ##viridis is the color map I need to display in
        self.s.step(10,.01)
        array = cm.viridis(self.s.get_density())
        array *= int(255/array.max())#normalize values
        data = array.astype(dtype = 'uint8')
        data = data.tobytes()
        #blit_buffer takes the data and put it onto my texture
        texture.blit_buffer(data,bufferfmt = 'ubyte', colorfmt = 'rgba')
        texture.flip_vertical()#kivy has y going up, not down

    def scroll_values(self, *args):
        self.s.V0 = args[1]

    #for getting the texture into the kivy file
    def get_texture(self):
        return texture

    def on_touch_move(self,touch):
        time1, time2, delta = 0,0,0.0
        graph_x, graph_y = 0.0,0.0
        time1 = time.time()
        #print("Touch called")
        #graph_x = (touch.x - (Lx/2)) * (16/Lx)# align touch with screen
        #graph_y = (touch.y - (Ly/2)) * (12/Ly)
        #self.potential = np.exp(-((UX - graph_x)**2 + (UY + graph_y)**2))
        self.s.y0 = (touch.x - (Lx/2)) * (16/Lx)# align touch with screen
        self.s.x0 = -(touch.y - (Ly/2)) * (12/Ly)

        self.push_to_texture()
        self.canvas.ask_update()
        #print(touch.pos)
        time2 = time.time()
        #delta = float(time2-time1)
        #print("touch duration:",delta)

    def update(self, dt):
        time1, time2, delta = 0.0,0.0,0.0
        time1 = time.time()
        #print("Update called")
        self.push_to_texture()
        self.canvas.ask_update()
        time2 = time.time()
        delta = float(time2-time1)
        #print("update duration:",delta)

class SuperHydroApp(App):
    Title = 'Super Hydro'

    def build(self):
        display = Display()
        Clock.schedule_interval(display.update,1.0/30.0)
        return display

if __name__ == "__main__":
    SuperHydroApp().run()
