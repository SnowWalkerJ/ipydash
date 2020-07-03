import base64
import functools
import html
import inspect
import io
import os


class Node:
    def __init__(self, name, *children, **attrs):
        self.name = name
        self.attrs = attrs
        self.children = list(children)

    def new_node(self, name, *children, cls=None, **attrs):
        if cls is None:
            cls = Node
        node = cls(name, *children, **attrs)
        self.children.append(node)
        return node

    def render(self, level=0):
        attrs = "".join(f" {key.replace('klass', 'class')}=\"{value}\"" for key, value in self.attrs.items())
        head = f"{' ' * level}<{self.name}{attrs}>"
        tail = f"{' ' * level}</{self.name}>"
        output = [head]
        for elem in self.children:
            if isinstance(elem, str):
                output.append(elem)
            else:
                output.extend(elem.render(level + 1))
        output.append(tail)
        return output

    def __str__(self):
        return "\n".join(self.render())


class Label(Node):
    def render(self, level):
        attrs = "".join(f" {key.replace('klass', 'class')}=\"{value}\"" for key, value in self.attrs.items())
        return [f"{' ' * level}<{self.name}{attrs}>"]


class Canvas(Node):
    def __init__(self, name, *children, level=1, **attrs):
        self.level = level
        super().__init__(name, *children, **attrs)

    def new_row(self, **attrs):
        return self.new_canvas(name="section", **attrs)

    def hr(self):
        self.new_label("hr")

    def title(self, text):
        return self.new_node(f"h{self.level}", text)

    def split(self, width):
        wl, wr = width, 10 - width
        row = self.new_node("div", klass="row", cls=Canvas)
        left = row.new_canvas(name="div", klass=f"c{wl}")
        right = row.new_canvas(name="div", klass=f"c{wr}")
        return left, right

    def text(self, msg):
        return self.new_node("p", html.escape(msg).replace("\n", "<br>"))

    def figure(self, fig):
        with io.BytesIO() as f:
            fig.savefig(f, bbox_inches='tight')
            f.seek(0)
            b64 = base64.b64encode(f.read()).decode()
        self.new_label("img", src=f"data:image/png;base64, {b64}")

    def table(self, dataframe):
        self.children.extend(dataframe.style.render().split("\n"))

    def code(self, code):
        node = self.new_node("pre")
        code = code.split("\n")
        node.new_node("code", *code, klass="lang-python")

    def new_label(self, name, **attrs):
        self.children.append(Label(name, **attrs))

    def new_canvas(self, name, level=None, **attrs):
        if level is None:
            level = self.level + 1
        return self.new_node(name, cls=Canvas, level=level, **attrs)


class HTML(Canvas):
    def __init__(self, title):
        self._title = title
        super().__init__(name="html")
        head = super().new_node("head")
        head.new_node("title", title)
        body = super().new_canvas(name="body")
        self.frame = body.new_canvas(name="div", level=1, klass="frame")

    @functools.wraps(Canvas.new_row)
    def new_row(self, *args, **kwargs):
        return self.frame.new_row(*args, **kwargs)

    @functools.wraps(Canvas.hr)
    def hr(self, *args, **kwargs):
        return self.frame.hr(*args, **kwargs)

    @functools.wraps(Canvas.title)
    def title(self, *args, **kwargs):
        return self.frame.title(*args, **kwargs)

    @functools.wraps(Canvas.split)
    def split(self, *args, **kwargs):
        return self.frame.split(*args, **kwargs)

    @functools.wraps(Canvas.text)
    def text(self, *args, **kwargs):
        return self.frame.text(*args, **kwargs)

    @functools.wraps(Canvas.figure)
    def figure(self, *args, **kwargs):
        return self.frame.figure(*args, **kwargs)

    @functools.wraps(Canvas.table)
    def table(self, *args, **kwargs):
        return self.frame.table(*args, **kwargs)

    @functools.wraps(Canvas.code)
    def code(self, *args, **kwargs):
        return self.frame.code(*args, **kwargs)

    @functools.wraps(Canvas.new_canvas)
    def new_canvas(self, *args, **kwargs):
        return self.frame.new_canvas(*args, **kwargs)

    @functools.wraps(Canvas.new_label)
    def new_label(self, *args, **kwargs):
        return self.frame.new_label(*args, **kwargs)
