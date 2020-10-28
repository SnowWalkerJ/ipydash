import contextlib
import functools
import inspect
import io
import os
import pprint
import traceback

import fire
import pandas as pd

from .canvas import HTML, Canvas


class Dashboard:
    def __init__(self, title, style="default"):
        import matplotlib as mpl
        mpl.use("agg")
        self.canvas = HTML(title)
        self.canvas.title(title)
        self.current_canvas: Canvas = self.canvas
        self.add_scripts(style)

    def add_scripts(self, style):
        html = super(HTML, self.canvas)
        style_path = os.path.join(os.path.dirname(__file__), "static", style)
        for filename in os.listdir(style_path):
            suffix = filename.split(".")[-1]
            if suffix not in ["css", "js"]:
                continue
            node_type = "style" if suffix == "css" else "script"
            with open(os.path.join(style_path, filename)) as f:
                script = f.read()
            html.new_node(node_type, script)
        html.new_node("script", "hljs.initHighlightingOnLoad();")

    def input(self, code):
        input_frame = self.current_canvas.new_canvas(name="div", klass="input")
        input_frame.code(code)

    def write(self, text):
        self.output(text)

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
        section = self.canvas.new_row()
        section.title(title)
        self.current_canvas = section
        return section

    def show(self):
        print(str(self.canvas))


class DashboardMeta(type):
    def __new__(cls, name, bases, members):
        for key, value in members.items():
            if inspect.isfunction(value) and not key.startswith("_"):
                members[key] = cls.wrap(value)
        if not any(issubclass(base, Dashboard) for base in bases):
            bases = tuple(list(bases) + [Dashboard])
        return type(name, bases, members)

    @staticmethod
    def wrap(function):
        def clean_code(code):
            code = code.split("\n")[1:-1]
            common_indent = min(len(line) - len(line.lstrip()) for line in code)
            code = [line[common_indent:] for line in code]
            return "\n".join(code)

        @functools.wraps(function)
        def wrapped(self, *args, **kwargs):
            import matplotlib.pyplot as plt
            sig = inspect.signature(function)
            params = sig.bind(self, *args, **kwargs)
            params.apply_defaults()
            arguments = ", ".join(f"{key}={repr(value)}" for key, value in params.arguments.items() if key != "self")
            title = f"{function.__name__}({arguments})"
            self.new_section(title)
            self.input(clean_code(inspect.getsource(function)))
            try:
                with contextlib.redirect_stdout(self):
                    function(self, *args, **kwargs)
            except Exception:
                self.output(traceback.format_exc())
            if plt.get_fignums():
                self.output(plt.gcf())
                plt.close('all')
            return self
        return wrapped
