---
jupytext:
  formats: ipynb,md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.10.3
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

```{raw-cell}
In creating a new application, kivy uses .kv files to simplify management of the widgets of the program. 'Widget' in kivy is any object that recieves input events, visual or not. Creating a Hello World application can be  done by creating a class with an 'App' property, and building it. Apps are started by calling the '.run()' element of your App class.
```

```{code-cell} ipython3
from kivy.app import App
from kivy.uix.label import Label

class MyTestApp(App):
    def build(self):
        return Label(text = 'Hello World') 
    
if __name__ == "__main__":
    MyTestApp().run()
```

```{raw-cell}
An important thing to note is that when a .kv file is created for this application, its name must mirror the class name where the app is built for kivy to associate the file correctly. For the above example, acceptable .kv file names would be:
    MyTestApp.kv
    MyTest.kv
Convention usually includes 'App' in the class name, but as long as the class has the 'App' property, leaving it out of both the class name and .kv file name still works.

The widget that is returned by the build becomes the root for a widget tree. All other widgets in the application are children of this root widget. Rather than being a widget directly, the return can also be to a class which has a kivy widget as its base. For example:
    class graph(BoxLayout)


Widgets:

Widgets, not to be confused with the Widget class, are contained in the kivy.uix module. General categories of widgets are: UX widgets, Layouts, Complex UX widgets, Behaviors widgets, and Screen manager. Whether its buttons, scroll bars, images, videos, or file selection, widgets encompass everything the user interacts with. In general, visual widgets all have methods to return information related to size, position, color, and so forth.

Input Handling:

Much of the input of an application is made through touch events. "on_touch_down()","on_touch_move()", and "on_touch_up()" are 3 examples of events which use the 'touch' keyword. Structurally, touches need to be in the same scope as the current loop being run. 
```

```{code-cell} ipython3
from kivy.app import App
from kivy.uix.button import Button

class MyGame(Button):
    def on_touch_down(self, touch):
        print("Button is pressed", touch.x, touch.y)
        
class GameApp(App):
    game = MyGame()
    game.text = "Hello World"
    return game    

if __name__ == "__main__":
    GameApp().run()
```

```{code-cell} ipython3
When the above example is run, it brings up an application window with "Hello World" in the center, and prints "Button is pressed" with the x,y position of the click to the console. 'touch' also has a 'pos' element. 'touch.pos' prints the position in a tuple.

If we wanted to change aspects of the button, such as the text it displays, it can be done through a .kv file as follows.
```

```{code-cell} ipython3
#Python File
class MyGame(BoxLayout):
    def change_button_text(self,widget,message):
        widget.text = message

class GameApp(App):
    return MyGame():
    
    
#Kivy File must start with "#:kivy <version>"
#:kivy 1.10.0

<MyGame>:
    Button:
        text: "Hello World"
        on_touch_down: self.text = "Goodbye" #directly modify button
        on_release: root.change_button_text(self,"Hello World") #indirectly modify button
    
```

```{code-cell} ipython3
There are two ways to modify widgets. The first way is to modify directly through the .kv file by calling an aspect of 'self', and the second is to call a function in the corresponding class in python and passing through the widget you want modified. 



Clock: 

Kivy has a built in module for scheduling events,creating event triggers, timing instances, and reporting real and average frames per second. The module location is "kivy.clock". Some of the most common methods are: schedule_interval(), schedule_once(), create_trigger(), unschedule(), get_fps(), get_rfps(), idle(). A full list can be found at: 
        https://kivy.org/docs/api-kivy.clock.html
```

```{code-cell} ipython3
from kivy.uix.widget import Widget
from kivy.clock import Clock

def Demo(Widget):
    time = 0
    def callback(self, dt):
        print("Current run time is: ", time, "seconds")
        self.time += 1
        #move objects, compute functions and so forth

def MyDemoApp(App):
    def build(self):
        example = Demo()
        Clock.schedule_interval(example.callback,1/1.)#fn parameters are: function to call, iterations per second

if __name__ == "__main__":
    MyDemoApp().run()
```

```{code-cell} ipython3
Graphing in Kivy:
    
Kivy does not have a built in way to put matplotlib plots into a kivy application, but fortunately, there is a package called kivy-garden that allows us to complete the task. It is important to note that every widget in kivy comes with a 'canvas' built into it, on which can be drawn the widgets shape, color, texture, and so forth. The usefulness of kivy-garden is that it allows us to draw a plot onto a canvas by treating the plot as a widget itself, and using the "add_widget()" method to paste it onto another kivy widget. 
```

```{code-cell} ipython3
import matplotlib
matplotlib.use('module://kivy.garden.matplotlib.backend_kivy')
import matplotlib.pyplot as plt
from matplotlib import cm

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout

import numpy as np

x = np.linspace(-10,10,100)
y = np.linspace(-10,10,100)
X,Y = np.meshgrid(x,y)
fig, ax = plt.subplots()
Z = (1/X) + (1/Y)
cs = ax.contourf(X,Y,Z,20,cmap = cm.viridis)
cs = fig.colorbar(cs)
fig.canvas.draw()

class MyGraphApp(App):
    def build(self):
        graph = BoxLayout()
        graph.add_widget(fig.canvas)
        return graph
    
if __name__ == "__main__":
    MyGraphApp().run()
```

```{code-cell} ipython3
Further information about kivy-garden can be found at:
    https://kivy.org/docs/api-kivy.garden.html
```
