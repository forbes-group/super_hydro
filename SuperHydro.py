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
from kivy.properties import ObjectProperty, NumericProperty
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.slider import Slider
from kivy.clock import Clock

#create a texture to draw the data on
Nxy = (64*2, 64*2)
texture = Texture.create(size = Nxy, colorfmt='rgba')

healing_length = 0.1
dt_t_scale = 1.0
steps = 20

#For scaling data
Winx = Window.width
Winy = Window.height

class Arrow(Widget):
    """def __init__(self,**kwargs):
        with self.canvas.before:
            PushMatrix
            self.rotation = Rotate(self.force_angle(), self.pos)
        with self.canvas.after:
            PopMatrix
        super().__init__(**kwargs)
        """
    def force_angle(self):
        print("THis is is the Arrow class")
        return 45

class Marker(Widget):
    #class for displaying finger and potential markers
    #all done in the .kv file
    pass

class Display(FloatLayout):
    potential = 0
    angle = NumericProperty(0)

    s = gpe.State(Nxy=Nxy, V0_mu=0.5, test_finger=False,
                  healing_length=healing_length, dt_t_scale=dt_t_scale)
    finger = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.push_to_texture()
        self.angle = 45
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

    def force_angle(self):
        dist_x = self.ids.finger.pos[0] - self.ids.potential.pos[0]
        dist_y = self.ids.finger.pos[1] - self.ids.potential.pos[1]
        if dist_x != 0:
            radians = np.arctan(dist_y / dist_x)
            if dist_x >= 0:
                print("radians:", radians)
                self.angle = int(np.degrees(radians) - 45)
                #print("degrees:", np.degrees(radians) - 45)
                #print("angle:", self.angle)
            else:
                self.angle = int(np.degrees(radians) + 135)
                #print("degrees: ", int(np.degrees(radians))+ 135)
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
        #time1, time2, delta = 0.0,0.0,0.0
        #time1 = time.time()
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
        #self.force_angle()
        self.push_to_texture()
        self.canvas.ask_update()
        #time2 = time.time()
        #delta = float(time2-time1)
        #print("update duration:",delta)

class SuperHydroApp(App):
    Title = 'Super Hydro'

    def build(self):
        display = Display()
        Clock.schedule_interval(display.update,1.0/20.0)
        return display

if __name__ == "__main__":
    SuperHydroApp().run()
