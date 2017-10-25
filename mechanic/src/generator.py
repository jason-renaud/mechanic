# native python
import os
import datetime
import pkg_resources
import shutil
import json

# third party
import yaml
import jinja2


class Generator:
    def __init__(self, directory, options=None):
        self.directory = directory
        self.options = options

    def create_dir_structure(self):
        try:
            os.makedirs(self.directory + "/controllers/__init__.py")
            os.makedirs(self.directory + "/models/__init__.py")
            os.makedirs(self.directory + "/schemas/__init__.py")
        except FileExistsError:
            # files already exist so we are good
            pass

