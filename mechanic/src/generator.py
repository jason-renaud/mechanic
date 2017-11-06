# native python
import os
import datetime
import pkg_resources
import shutil
import json
import datetime as dt

# third party
import yaml
import jinja2

# project
from mechanic.src.reader import APP_NAME_KEY
import mechanic.src.utils as utils


class Generator(object):
    def __init__(self, directory, mech_obj, options=None):
        self.directory = directory
        self.mech_obj = mech_obj
        self.options = options
        # self.root_dir = os.path.dirname(os.path.realpath(self.mechanic_file))

        self.TEMPLATE_DIR = "../templates/"

    def create_dir_structure(self):
        models_path = self.options["MODELS_PATH"]
        controllers_path = self.options["CONTROLLERS_PATH"]
        schemas_path = self.options["SCHEMAS_PATH"]
        try:
            os.makedirs(self.directory + "/" + schemas_path.rsplit("/", 1)[0])
            os.makedirs(self.directory + "/" + models_path.rsplit("/", 1)[0])
            os.makedirs(self.directory + "/" + controllers_path.rsplit("/", 1)[0])
        except FileExistsError:
            # files already exist so we are good
            pass

        for namespace, obj in self.mech_obj["namespaces"].items():
            filename = utils.replace_template_var(models_path, namespace=namespace, version=self.mech_obj["version"])
            self.build_models_file(filename, namespace)

    def build_models_file(self, filename, namespace):
        base_models = dict()
        namespaced_models = dict()

        for model_name, model in self.mech_obj["models"].items():
            if model["namespace"] == namespace:
                base_model_path = model["base_model_path"]
                base_model_name = model["base_model_name"]

                if not base_models.get(base_model_path):
                    base_models[base_model_path] = []

                if base_model_name not in base_models[base_model_path]:
                    base_models[base_model_path].append(base_model_name)

                namespaced_models[model_name] = model

        models_result = self._render(pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "models.tpl"), context={
            "timestamp": dt.datetime.utcnow(),
            "app_name": self.options[APP_NAME_KEY],
            "base_models": base_models,
            "models": namespaced_models
        })

        with open(self.directory + "/" + filename, "w") as f:
            f.write(models_result)


    def _render(self, tpl_path, context):
        path, filename = os.path.split(tpl_path)
        return jinja2.Environment(loader=jinja2.FileSystemLoader(path or "./")).get_template(filename).render(
            context)
