# native python
import os
import datetime
import pkg_resources
import shutil
import json

# third party
import yaml
import jinja2

# project
from .utils import deserialize_file


class Generator:
    def __init__(self, directory, mechanic_file, options=None):
        self.directory = directory
        self.mechanic_file = mechanic_file
        # self.mechanic_obj = deserialize_file(self.mechanic_file)
        self.options = options
        self.root_dir = os.path.dirname(os.path.realpath(self.mechanic_file))

    def create_dir_structure(self):
        models_path = self.options["MODELS_PATH"]
        controllers_path = self.options["CONTROLLERS_PATH"]
        schemas_path = self.options["SCHEMAS_PATH"]
        try:
            os.makedirs(self.directory + "/" + schemas_path)
            os.makedirs(self.directory + "/" + models_path)
            os.makedirs(self.directory + "/" + controllers_path)
        except FileExistsError:
            # files already exist so we are good
            pass


