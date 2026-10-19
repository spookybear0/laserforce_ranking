from functools import wraps
import types
import django
import sys
import os

def setup_environment():
    inner_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "laserforce_ranking"))

    submodule_package = types.ModuleType("laserforce_ranking")
    submodule_package.__path__ = [inner_folder]

    sys.modules["laserforce_ranking"] = submodule_package
    if inner_folder not in sys.path:
        sys.path.insert(0, inner_folder)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "laserforce_ranking.settings")
    django.setup()