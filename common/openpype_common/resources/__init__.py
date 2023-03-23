import os

RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))


def get_resource_path(*args):
    path_items = list(args)
    path_items.insert(0, RESOURCES_DIR)
    return os.path.sep.join(path_items)


def get_icon_path():
    return get_resource_path("openpype_icon.png")


def load_stylesheet():
    stylesheet_path = get_resource_path("stylesheet.css")

    with open(stylesheet_path, "r") as stream:
        content = stream.read()
    return content
