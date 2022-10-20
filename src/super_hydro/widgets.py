"""Widgets used to define a layout.

These are basically ipywidgets but with an added trait `name` that we
use to associate the widget with appropriate parameters in the client.
"""
import traitlets
import ipywidgets

from .clients.canvas_widget import Canvas, CanvasIPy

__all__ = [
    "density",
    "Checkbox",
    "ToggleButton",
    "Valid",
    "Button",
    "ButtonStyle",
    "Box",
    "HBox",
    "VBox",
    "GridBox",
    "FloatText",
    "BoundedFloatText",
    "FloatSlider",
    "FloatProgress",
    "FloatRangeSlider",
    "FloatLogSlider",
    "IntText",
    "BoundedIntText",
    "IntSlider",
    "IntProgress",
    "IntRangeSlider",
    "Layout",
    "Play",
    "SliderStyle",
    "ColorPicker",
    "DatePicker",
    "RadioButtons",
    "ToggleButtons",
    "ToggleButtonsStyle",
    "Dropdown",
    "Select",
    "SelectionSlider",
    "SelectMultiple",
    "SelectionRangeSlider",
    "Tab",
    "Accordion",
    "HTML",
    "HTMLMath",
    "Label",
    "Text",
    "Textarea",
    "Password",
    "Controller",
    "Image",
    "Video",
    "Audio",
    "Canvas",
    "get_descriptions",
    "get_interactive_and_special_widgets",
    "get_interactive_widgets",
]


class Checkbox(ipywidgets.Checkbox):
    name = traitlets.ObjectName("_").tag(sync=True)


class ToggleButton(ipywidgets.ToggleButton):
    name = traitlets.ObjectName("_").tag(sync=True)


class Valid(ipywidgets.Valid):
    name = traitlets.ObjectName("_").tag(sync=True)


class Button(ipywidgets.Button):
    name = traitlets.ObjectName("_").tag(sync=True)


class ButtonStyle(ipywidgets.ButtonStyle):
    name = traitlets.ObjectName("_").tag(sync=True)


class Box(ipywidgets.Box):
    name = traitlets.ObjectName("_").tag(sync=True)


class HBox(ipywidgets.HBox):
    name = traitlets.ObjectName("_").tag(sync=True)


class VBox(ipywidgets.VBox):
    name = traitlets.ObjectName("_").tag(sync=True)


class GridBox(ipywidgets.GridBox):
    name = traitlets.ObjectName("_").tag(sync=True)


class FloatText(ipywidgets.FloatText):
    name = traitlets.ObjectName("_").tag(sync=True)


class BoundedFloatText(ipywidgets.BoundedFloatText):
    name = traitlets.ObjectName("_").tag(sync=True)


class FloatSlider(ipywidgets.FloatSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class FloatProgress(ipywidgets.FloatProgress):
    name = traitlets.ObjectName("_").tag(sync=True)


class FloatRangeSlider(ipywidgets.FloatRangeSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class FloatLogSlider(ipywidgets.FloatLogSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class IntText(ipywidgets.IntText):
    name = traitlets.ObjectName("_").tag(sync=True)


class BoundedIntText(ipywidgets.BoundedIntText):
    name = traitlets.ObjectName("_").tag(sync=True)


class IntSlider(ipywidgets.IntSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class IntProgress(ipywidgets.IntProgress):
    name = traitlets.ObjectName("_").tag(sync=True)


class IntRangeSlider(ipywidgets.IntRangeSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class Play(ipywidgets.Play):
    name = traitlets.ObjectName("_").tag(sync=True)


class SliderStyle(ipywidgets.SliderStyle):
    name = traitlets.ObjectName("_").tag(sync=True)


class ColorPicker(ipywidgets.ColorPicker):
    name = traitlets.ObjectName("_").tag(sync=True)


class DatePicker(ipywidgets.DatePicker):
    name = traitlets.ObjectName("_").tag(sync=True)


class RadioButtons(ipywidgets.RadioButtons):
    name = traitlets.ObjectName("_").tag(sync=True)


class ToggleButtons(ipywidgets.ToggleButtons):
    name = traitlets.ObjectName("_").tag(sync=True)


class ToggleButtonsStyle(ipywidgets.ToggleButtonsStyle):
    name = traitlets.ObjectName("_").tag(sync=True)


class Dropdown(ipywidgets.Dropdown):
    name = traitlets.ObjectName("_").tag(sync=True)


class Select(ipywidgets.Select):
    name = traitlets.ObjectName("_").tag(sync=True)


class SelectionSlider(ipywidgets.SelectionSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class SelectMultiple(ipywidgets.SelectMultiple):
    name = traitlets.ObjectName("_").tag(sync=True)


class SelectionRangeSlider(ipywidgets.SelectionRangeSlider):
    name = traitlets.ObjectName("_").tag(sync=True)


class Tab(ipywidgets.Tab):
    name = traitlets.ObjectName("_").tag(sync=True)


class Accordion(ipywidgets.Accordion):
    name = traitlets.ObjectName("_").tag(sync=True)


class HTML(ipywidgets.HTML):
    name = traitlets.ObjectName("_").tag(sync=True)


class HTMLMath(ipywidgets.HTMLMath):
    name = traitlets.ObjectName("_").tag(sync=True)


class Label(ipywidgets.Label):
    name = traitlets.ObjectName("_").tag(sync=True)


class Text(ipywidgets.Text):
    name = traitlets.ObjectName("_").tag(sync=True)


class Textarea(ipywidgets.Textarea):
    name = traitlets.ObjectName("_").tag(sync=True)


class Password(ipywidgets.Password):
    name = traitlets.ObjectName("_").tag(sync=True)


class Controller(ipywidgets.Controller):
    name = traitlets.ObjectName("_").tag(sync=True)


class Image(ipywidgets.Image):
    name = traitlets.ObjectName("_").tag(sync=True)


class Video(ipywidgets.Video):
    name = traitlets.ObjectName("_").tag(sync=True)


class Audio(ipywidgets.Audio):
    name = traitlets.ObjectName("_").tag(sync=True)


class Layout(ipywidgets.Layout):
    name = traitlets.ObjectName("_").tag(sync=True)


######################################################################
# Special widgets that should always be included.
# density = Canvas(name="density")
density = CanvasIPy(name="density", layout=Layout(width="100%", height="auto"))
reset = Button(name="reset", description="Reset", layout=dict(width="5em"))
reset_tracers = Button(
    name="reset_tracers", description="Reset Tracers", layout=dict(width="8em")
)
fps = IntSlider(20, 0, 60, name="fps")
quit = Button(name="quit", description="Quit", layout=dict(width="4em"))
messages = Label("Messages", name="messages")
controls = HBox([quit, reset, reset_tracers, fps, messages], name="controls")
special_widget_names = set(
    ["density", "quit", "reset", "reset_tracers", "fps", "messages", "controls"]
)


######################################################################
# Helpers
def get_descriptions(layout):
    """Return a dictionary of all descriptions."""
    # Walk through layout and gather widgets with names.
    descriptions = {}

    def walk(root):
        if root.name != "_":
            descriptions[root.name] = getattr(root, "description", root.name)
        list(map(walk, getattr(root, "children", [])))

    walk(layout)
    return descriptions


def get_interactive_and_special_widgets(layout):
    """Return a set of interactive widgets - those with a valid `name`"""

    # Walk through layout and gather widgets with names so we can
    # set those default values.
    interactive_widgets = set()
    special_widgets = {}

    def walk(root):
        if root.name in special_widget_names:
            special_widgets[root.name] = root
        elif root.name != "_":
            interactive_widgets.add(root)
        list(map(walk, getattr(root, "children", [])))

    walk(layout)
    return (interactive_widgets, special_widgets)


def get_interactive_widgets(layout):
    """Return a set of interactive widgets - those with a valid `name`"""
    return get_interactive_and_special_widgets(layout)[0]
