import json
import sys
import os
from db.config import get_tortoise_orm_config

def is_in_ipython() -> bool:
    try:
        __IPYTHON__
        return True
    except NameError:
        return False

path = os.path.dirname(os.path.realpath(__file__))

default_config = {
    "db_host": "localhost",
    "db_user": "root",
    "db_password": "",
    "db_port": 3306,
    "db_name": "laserforce",
    "sentry_dsn": "",
    "sentry_environment": "production",
    "redis": "redis://localhost",
}

config_options = list(default_config.keys())

class JsonFile:
    def __init__(self, file_name: str) -> None:
        self.file = None
        self.file_name = file_name
        if os.path.exists(file_name):
            with open(file_name) as f:
                self.file = json.load(f)

    def get_file(self) -> dict:
        """Returns the loaded JSON file as a dict."""
        return self.file

    def write_file(self, new_content: dict) -> None:
        """Writes a new dict to the file."""
        with open(self.file_name, "w") as f:
            json.dump(new_content, f, indent=4)
        self.file = new_content


jconfig = JsonFile(path + "/config.json")
config = jconfig.get_file()

if config is None:
    print("Generating new config")
    jconfig.write_file(default_config)
    print("Generated new config! Please edit it and restart laserforce_ranking.")
    raise SystemExit

# check for config updates
config_keys = list(config.keys())
updated_conf = False

for def_conf_option in config_options:
    if def_conf_option not in config_keys:
        updated_conf = True
        config[def_conf_option] = default_config[def_conf_option]

if updated_conf:
    jconfig.write_file(config)
    print("Your config has been updated! Please change the new vaulues to your liking.")


    if "pytest" not in sys.modules and not is_in_ipython():
        raise SystemExit
    
TORTOISE_ORM = get_tortoise_orm_config(config)