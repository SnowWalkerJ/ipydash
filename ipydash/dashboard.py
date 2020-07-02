import functools
import inspect
import io
import pprint
import traceback

import fire
import pandas as pd

from .canvas import HTML, Canvas


class Dashboard:
    def __init__(self, title):
        import matplotlib as mpl
        mpl.use("agg")
        self.canvas = HTML(title)
        self.canvas.title(title)
        self.current_canvas: Canvas = self.canvas

    def output(self, obj):
        try:
            from matplotlib.figure import Figure
        except ImportError:
            Figure = type(None)
        try:
            from pandas import DataFrame
        except ImportError:
            DataFrame = type(None)

        if isinstance(obj, Figure):
            self.current_canvas.figure(obj)
        elif isinstance(obj, DataFrame):
            self.current_canvas.table(obj)
        elif isinstance(obj, str):
            self.current_canvas.text(obj)
        else:
            with io.StringIO() as f:
                pprint.pprint(obj, f)
                f.seek(0)
                self.current_canvas.text(f.read())

    def new_section(self, title):
        section = self.current_canvas.new_row()
        section.title(title)
        self.current_canvas = section
        return section


class DashboardMeta(type):
    def __new__(cls, name, bases, members):
        for key, value in members.items():
            if inspect.isfunction(value) and key != "__init__":
                members[key] = cls.wrap(value)
        if not any(issubclass(base, Dashboard) for base in bases):
            bases = tuple(list(bases) + [Dashboard])
        return type(name, bases, members)

    @staticmethod
    def wrap(function)
        @functools.wraps(function)
        def wrapped(self, *args, **kwargs):
            stack = traceback.extract_stack()
            if len(stack) >=2 and stack[-2].name == "_CallAndUpdateTrace":
                import matplotlib.pyplot as plt
                sig = inspect.signature(function)
                params = sig.bind(self, *args, **kwargs)
                params.apply_defaults()
                arguments = ", ".join(f"{key}={repr(value)}" for key, value in params.arguments.items() if key != "self")
                title = f"{function.__name__}({arguments})"
                self.new_section(title)
                function(self, *args, **kwargs)
                if plt.gcf().get_axes():
                    self.output(plt.gcf())
                    plt.clf()
                return self
            else:
                return function(self, *args, **kwargs)
        return wrapped
