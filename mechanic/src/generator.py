# native python
import os
import datetime
import pkg_resources
import shutil
import json
import datetime as dt
import errno

# third party
import yaml
import jinja2

# project
from mechanic.src import reader
import mechanic.src.utils as utils


# Taken from https://stackoverflow.com/questions/23793987/python-write-file-to-directory-doesnt-exist
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def safe_open_w(path):
    """ Open "path" for writing, creating any parent directories as needed.
    """
    mkdir_p(os.path.dirname(path))
    return open(path, 'w')


class Generator(object):
    def __init__(self, directory, mech_obj, options=None):
        self.directory = directory
        self.mech_obj = mech_obj
        self.options = options

        self.TEMPLATE_DIR = "../templates/"

    def generate(self):
        models_path = self.options[reader.MODELS_PATH_KEY]
        controllers_path = self.options[reader.CONTROLLERS_PATH_KEY]
        schemas_path = self.options[reader.SCHEMAS_PATH_KEY]

        for namespace, obj in self.mech_obj["namespaces"].items():
            model_filename = utils.replace_template_var(models_path,
                                                        namespace=namespace,
                                                        version=self.mech_obj["version"])
            schema_filename = utils.replace_template_var(schemas_path,
                                                         namespace=namespace,
                                                         version=self.mech_obj["version"])

            controller_filename = utils.replace_template_var(controllers_path,
                                                             namespace=namespace,
                                                             version=self.mech_obj["version"])

            if self.options[reader.EXCLUDE_MODEL_GENERATION_KEY] != "all":
                self.build_models_file(model_filename, namespace)
            if self.options[reader.EXCLUDE_SCHEMA_GENERATION_KEY] != "all":
                self.build_schemas_file(schema_filename, namespace)
            if self.options[reader.EXCLUDE_CONTROLLER_GENERATION_KEY] != "all":
                self.build_controllers_file(controller_filename, namespace)

        # add mechanic folder
        self._add_mechanic_base_package()

        # add starter app files
        if self.options[reader.APP_NAME_KEY] + "/__init__.py" not in self.options[reader.EXCLUDE_KEY]:
            self.build_init_app_file()
        if "run.py" not in self.options[reader.EXCLUDE_KEY]:
            self._add_run_file()
        if "requirements.txt" not in self.options[reader.EXCLUDE_KEY]:
            self._add_requirements_txt()
        if self.options[reader.APP_NAME_KEY] + "/init_api.py" not in self.options[reader.EXCLUDE_KEY]:
            self.build_init_api_file()
        self._add_swagger_docs()

    def build_models_file(self, filename, namespace):
        base_models = dict()
        namespaced_models = dict()
        namespaced_many_to_many = dict()

        for model_name, model in self.mech_obj["models"].items():
            if model["namespace"] == namespace:
                base_model_path = model["base_model_path"]
                base_model_name = model["base_model_name"]

                if not base_models.get(base_model_path):
                    base_models[base_model_path] = []

                if base_model_name not in base_models[base_model_path]:
                    base_models[base_model_path].append(base_model_name)

                namespaced_models[model_name] = model

        for m2m_key, m2m in self.mech_obj["many_to_many"].items():
            if m2m["namespace"] == namespace:
                namespaced_many_to_many[m2m_key] = m2m

        if len(namespaced_models):
            models_result = self._render(pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "models.tpl"), context={
                "timestamp": dt.datetime.utcnow(),
                "app_name": self.options[reader.APP_NAME_KEY],
                "base_models": base_models,
                "models": namespaced_models,
                "many_to_many": namespaced_many_to_many
            })

            module_paths = dict()
            for k, v in namespaced_models.items():
                if not module_paths.get(v["module_path"]):
                    module_paths[v["module_path"]] = []
                module_paths[v["module_path"]].append(k)

            self._write_if_not_excluded(filename, models_result)

    def build_schemas_file(self, filename, namespace):
        base_schemas = dict()
        namespaced_schemas = dict()
        dependent_models = dict()

        for schema_name, schema in self.mech_obj["schemas"].items():
            if schema["namespace"] == namespace:
                base_schema_path = schema["base_schema_path"]
                base_schema_name = schema["base_schema_name"]

                schema_model = schema["model"]
                if schema_model:
                    path = self.mech_obj["models"][schema_model]["module_path"]

                    if not dependent_models.get(path):
                        dependent_models[path] = []
                    dependent_models[path].append(schema_model)

                if not base_schemas.get(base_schema_path):
                    base_schemas[base_schema_path] = []

                if base_schema_name not in base_schemas[base_schema_path]:
                    base_schemas[base_schema_path].append(base_schema_name)

                namespaced_schemas[schema_name] = schema

        if len(namespaced_schemas):
            schemas_result = self._render(pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "schemas.tpl"), context={
                "timestamp": dt.datetime.utcnow(),
                "app_name": self.options[reader.APP_NAME_KEY],
                "base_schemas": base_schemas,
                "schemas": namespaced_schemas,
                "dependent_models": dependent_models
            })

            self._write_if_not_excluded(filename, schemas_result)

    def build_controllers_file(self, filename, namespace):
        base_controllers = dict()
        namespaced_controllers = dict()
        dependent_models = dict()
        dependent_schemas = dict()

        for controller_name, controller in self.mech_obj["controllers"].items():
            if controller["namespace"] == namespace:
                base_controller_path = controller["base_controller_path"]
                base_controller_name = controller["base_controller_name"]

                resource = controller["resource"]

                model = self.mech_obj["resources"].get(resource, {}).get("model")
                schema = self.mech_obj["resources"].get(resource, {}).get("schema")
                request_schemas = [controller.get("requests", {}).get("post", {}).get("schema"),
                                   controller.get("requests", {}).get("put", {}).get("schema"),
                                   controller.get("requests", {}).get("delete", {}).get("schema"),
                                   controller.get("requests", {}).get("get", {}).get("schema")]
                request_schemas = [item for item in request_schemas if item]

                if model:
                    model_path = self.mech_obj["models"][model]["module_path"]

                    if not dependent_models.get(model_path):
                        dependent_models[model_path] = []

                    if model not in dependent_models[model_path]:
                        dependent_models[model_path].append(model)

                if schema:
                    schema_path = self.mech_obj["schemas"][schema]["module_path"]

                    if not dependent_schemas.get(schema_path):
                        dependent_schemas[schema_path] = []

                    if schema not in dependent_schemas[schema_path]:
                        dependent_schemas[schema_path].append(schema)

                    for item in request_schemas:
                        request_schema_path = self.mech_obj["schemas"][schema]["module_path"]
                        if item not in dependent_schemas[request_schema_path]:
                            dependent_schemas[request_schema_path].append(item)

                if not base_controllers.get(base_controller_path):
                    base_controllers[base_controller_path] = []

                if base_controller_name not in base_controllers[base_controller_path]:
                    base_controllers[base_controller_path].append(base_controller_name)

                namespaced_controllers[controller_name] = controller

        if len(namespaced_controllers):
            result = self._render(pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "controllers.tpl"), context={
                "timestamp": dt.datetime.utcnow(),
                "app_name": self.options[reader.APP_NAME_KEY],
                "base_controllers": base_controllers,
                "controllers": namespaced_controllers,
                "dependent_models": dependent_models,
                "dependent_schemas": dependent_schemas,
            })

            self._write_if_not_excluded(filename, result)

    def build_init_app_file(self):
        dependent_controllers = dict()

        for controller_name, controller in self.mech_obj["controllers"].items():
            controller_path = controller["module_path"]
            if not dependent_controllers.get(controller_path):
                dependent_controllers[controller_path] = []

            if controller_name not in dependent_controllers[controller_path]:
                dependent_controllers[controller_path].append(controller_name)

        result = self._render(pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "init_app.tpl"), context={
            "timestamp": dt.datetime.utcnow(),
            "app_name": self.options[reader.APP_NAME_KEY],
            "dependent_controllers": dependent_controllers,
            "controllers": self.mech_obj["controllers"],
            "base_api_path": self.options[reader.BASE_API_PATH_KEY],
            "db_url": self.options[reader.DATABASE_URL_KEY]
        })

        app_name = self.options[reader.APP_NAME_KEY]
        with safe_open_w(self.directory + "/" + app_name + "/__init__.py") as f:
            f.write(result)

    def build_init_api_file(self):
        dependent_controllers = dict()
        api_controllers = []

        for controller_name, controller in self.mech_obj["controllers"].items():
            if controller["oapi_uri"] not in self.options[reader.OVERRIDE_CONTROLLER_FOR_URI_KEY].keys():
                controller_path = controller["module_path"]
            else:
                overridden_path = self.options[reader.OVERRIDE_CONTROLLER_FOR_URI_KEY][controller["oapi_uri"]]
                controller_path = overridden_path.rsplit(".", 1)[0]
                controller_name = overridden_path.rsplit(".", 1)[1]

            api_controllers.append({
                "uri": controller["uri"],
                "name": controller_name
            })

            if not dependent_controllers.get(controller_path):
                dependent_controllers[controller_path] = []

            if controller_name not in dependent_controllers[controller_path]:
                dependent_controllers[controller_path].append(controller_name)

        result = self._render(pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "init_api.tpl"), context={
            "timestamp": dt.datetime.utcnow(),
            "app_name": self.options[reader.APP_NAME_KEY],
            "dependent_controllers": dependent_controllers,
            "controllers": api_controllers,
            "base_api_path": self.options[reader.BASE_API_PATH_KEY],
            "db_url": self.options[reader.DATABASE_URL_KEY]
        })

        app_name = self.options[reader.APP_NAME_KEY]
        with safe_open_w(self.directory + "/" + app_name + "/init_api.py") as f:
            f.write(result)

    def _write_if_not_excluded(self, filename, contents):
        if filename not in self.options[reader.EXCLUDE_KEY]:
            self._add_package_files(filename)
            with safe_open_w(self.directory + "/" + filename) as f:
                f.write(contents)

    def _add_run_file(self):
        self._replace_app_name_in_file(pkg_resources.resource_filename(__name__, "../mechanic/run.py"),
                                       self.directory + "/run.py")

    def _add_requirements_txt(self):
        shutil.copy(pkg_resources.resource_filename(__name__, "../mechanic/requirements.txt"),
                    self.directory + "/requirements.txt")

    def _add_mechanic_base_package(self):
        mechanic_folder = pkg_resources.resource_filename(__name__, "../mechanic/base/")
        mechanic_utils_folder = pkg_resources.resource_filename(__name__, "../mechanic/utils/")

        try:
            shutil.copytree(mechanic_folder, self.directory + "/mechanic/base/")
            self._add_package_files("mechanic/base/")
        except FileExistsError as e:
            pass

        try:
            shutil.copytree(mechanic_utils_folder, self.directory + "/mechanic/utils/")
            self._add_package_files("mechanic/utils/")
        except FileExistsError as e:
            pass

        self._replace_app_name_in_file(pkg_resources.resource_filename(__name__, "../mechanic/base/schemas.py"),
                                       self.directory + "/mechanic/base/schemas.py")
        self._replace_app_name_in_file(pkg_resources.resource_filename(__name__, "../mechanic/base/models.py"),
                                       self.directory + "/mechanic/base/models.py")
        self._replace_app_name_in_file(pkg_resources.resource_filename(__name__, "../mechanic/base/controllers.py"),
                                       self.directory + "/mechanic/base/controllers.py")
        self._replace_app_name_in_file(pkg_resources.resource_filename(__name__, "../mechanic/utils/db_helper.py"),
                                       self.directory + "/mechanic/utils/db_helper.py")

    def _add_swagger_docs(self):
        static_folder = pkg_resources.resource_filename(__name__, "../mechanic/app/static")
        templates_folder = pkg_resources.resource_filename(__name__, "../mechanic/app/templates")

        try:
            shutil.copytree(static_folder, self.directory + "/" + self.options[reader.APP_NAME_KEY] + "/static")
        except FileExistsError:
             pass
        try:
            shutil.copytree(templates_folder, self.directory + "/" + self.options[reader.APP_NAME_KEY] + "/templates")
        except FileExistsError:
             pass

        # temp.yaml is the merged specification file generated from the compiler. Copy this to the static folder and
        # then delete the temp.yaml file
        oapi_file_location = self.directory + "/temp.yaml"
        shutil.copy(oapi_file_location, self.directory + "/" + self.options[reader.APP_NAME_KEY] + "/static/docs.yaml")
        os.remove(oapi_file_location)

    def _add_package_files(self, path, imports=None):
        dirs = path.split("/")
        dir_path = []
        for i, dir in enumerate(dirs):
            dir_path.append("/".join(dirs[:(i+1)]))

        for dir in dir_path:
            if not dir.endswith(".py"):
                import_result = imports
                if imports:
                    import_result = self._render(
                        pkg_resources.resource_filename(__name__, self.TEMPLATE_DIR + "init_models.tpl"),
                        context={
                            "module_paths": imports
                        })
                if not os.path.exists(self.directory + "/" + dir + "/__init__.py"):
                    with safe_open_w(self.directory + "/" + dir + "/__init__.py") as f:
                        if import_result:
                            f.write(import_result)
                else:
                    with open(self.directory + "/" + dir + "/__init__.py", "r") as f:
                        current_contents = f.read()

                    with open(self.directory + "/" + dir + "/__init__.py", "a") as f:
                        if import_result and import_result not in current_contents:
                            f.write(import_result)

    def _replace_app_name_in_file(self, src_file, output_file):
        # replace app_name var
        result = self._render(src_file, context={
            "timestamp": dt.datetime.utcnow(),
            "app_name": self.options[reader.APP_NAME_KEY]
        })

        with safe_open_w(output_file) as f:
            f.write(result)

    def _render(self, tpl_path, context):
        path, filename = os.path.split(tpl_path)
        return jinja2.Environment(loader=jinja2.FileSystemLoader(path or "./")).get_template(filename).render(
            context)
