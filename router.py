import os
import sys
from aiohttp import web
from shared import routes
from importlib import import_module

path = os.path.dirname(os.path.abspath(__file__)) + "/"

def add_all_routes(app: web.Application):
    def import_dir(directory):
        sys.path.append(directory)
        for f in os.listdir(directory):
            if os.path.isdir(directory + f) and f not in ["__pycache__"]:
                import_dir(directory + f + "/")
            elif os.path.isfile(directory + f) and f not in ["__init__.py"]:
                __import__(f.rstrip(".py"))
    import_dir(path + "handlers/")
    app.add_routes(routes)