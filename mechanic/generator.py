import os
import datetime
import pkg_resources
import shutil
import json
import yaml
import jinja2


class Generator:
    def __init__(self, mechanic_file, mechanic_conf, output_dir, app_name=None):
        self.mechanic_file = mechanic_file
        self.mechanic_obj = self._deserialize_file()
        self.mechanic_conf = mechanic_conf
        self.output_dir = output_dir
        self.BASE_INIT_SRC = pkg_resources.resource_filename(__name__, "starter/base/__init__.py")
        self.BASE_INIT_OUTPUT = os.path.expanduser(self.output_dir + "/base/")
        self.BASE_CONTROLLERS_SRC = pkg_resources.resource_filename(__name__, "starter/base/controllers.py")
        self.BASE_CONTROLLERS_OUTPUT = os.path.expanduser(self.output_dir + "/base/")
        self.BASE_SCHEMAS_SRC = pkg_resources.resource_filename(__name__, "starter/base/schemas.py")
        self.BASE_SCHEMAS_OUTPUT = os.path.expanduser(self.output_dir + "/base/")
        self.BASE_EXCEPTIONS_SRC = pkg_resources.resource_filename(__name__, "starter/base/exceptions.py")
        self.BASE_EXCEPTIONS_OUTPUT = os.path.expanduser(self.output_dir + "/base/")
        self.BASE_FIELDS_SRC = pkg_resources.resource_filename(__name__, "starter/base/fields.py")
        self.BASE_FIELDS_OUTPUT = os.path.expanduser(self.output_dir + "/base/")
        self.BASE_DB_HELPER_SRC = pkg_resources.resource_filename(__name__, "starter/base/db_helper.py")
        self.BASE_DB_HELPER_OUTPUT = os.path.expanduser(self.output_dir + "/base/")
        self.APP_INIT_SRC = pkg_resources.resource_filename(__name__, "starter/app/__init__.py")
        self.APP_INIT_OUTPUT = os.path.expanduser(self.output_dir + "/app/__init__.py")
        self.APP_RUN_SRC = pkg_resources.resource_filename(__name__, "starter/run.py")
        self.APP_RUN_OUTPUT = os.path.expanduser(self.output_dir + "/")
        self.BASE_REQUIREMENTS_SRC = pkg_resources.resource_filename(__name__, "starter/requirements.txt")
        self.BASE_REQUIREMENTS_OUTPUT = os.path.expanduser(self.output_dir + "/")
        self.BASE_CONFIG_SRC = pkg_resources.resource_filename(__name__, "starter/app/config.py")
        self.BASE_CONFIG_OUTPUT = os.path.expanduser(self.output_dir + "/app/config.py")
        self.API_ENDPOINTS_PATH = os.path.expanduser(self.output_dir + "/app/api.py")
        self.API_CONTROLLERS_PATH = os.path.expanduser(self.output_dir + "/controllers/")
        self.API_MODELS_PATH = os.path.expanduser(self.output_dir + "/models/")
        self.API_SCHEMAS_PATH = os.path.expanduser(self.output_dir + "/schemas/")

        if app_name is None:
            self.app_name = self.output_dir.split("/")[-1]

    def generate(self):
        print("\n\n###")
        if not os.path.exists(os.path.expanduser(self.output_dir + "/app/")):
            os.makedirs(os.path.expanduser(self.output_dir + "/app/"))
        if not os.path.exists(os.path.expanduser(self.output_dir + "/base/")):
            os.makedirs(os.path.expanduser(self.output_dir + "/base/"))

        self.generate_starter_files(all=True)
        self.generate_models()
        self.generate_schemas()
        self.generate_controllers()
        self.generate_api_endpoints()

    def generate_models(self):
        import_modules = ""
        for namespace, namespace_obj in self.mechanic_obj["namespaces"].items():
            data = dict()
            data["models"] = dict()
            data["many_to_many_models"] = dict()

            for model_key in namespace_obj["models"]:
                data["models"][model_key] = self.mechanic_obj["models"][model_key]

            # for many_to_many_key in namespace_obj["many_to_many"]:
            #     data["many_to_many_models"][many_to_many_key] = self.mechanic_obj["many_to_many_models"][many_to_many_key]

            models_result = self._render(pkg_resources.resource_filename(__name__, "templates/models.tpl"),
                                        {
                                            "data": data,
                                            "fkeys": self.mechanic_obj["fkeys"],
                                            "timestamp": datetime.datetime.utcnow()
                                        })

            models_output = self.API_MODELS_PATH + namespace
            if not os.path.exists(models_output):
                os.makedirs(models_output)

            import_modules = import_modules + "from models." + namespace + ".models import *\n"
            with open(models_output + "/__init__.py", "w"):
                pass

            with open(models_output + "/models.py", "w") as f:
                f.write(models_result)

        with open(self.API_MODELS_PATH + "/__init__.py", "w") as f:
            f.write(import_modules)

    def generate_schemas(self):
        import_modules = ""
        for namespace, namespace_obj in self.mechanic_obj["namespaces"].items():
            data = dict()

            for schema_key in namespace_obj["mschemas"]:
                data[schema_key] = self.mechanic_obj["mschemas"][schema_key]

            schemas_result = self._render(pkg_resources.resource_filename(__name__, "templates/schemas.tpl"),
                                        {
                                            "data": data,
                                            "timestamp": datetime.datetime.utcnow()
                                        })

            schemas_output = self.API_SCHEMAS_PATH + namespace
            if not os.path.exists(schemas_output):
                os.makedirs(schemas_output)

            import_modules = import_modules + "from schemas." + namespace + ".schemas import *\n"
            with open(schemas_output + "/__init__.py", "w"):
                pass

            with open(schemas_output + "/schemas.py", "w") as f:
                f.write(schemas_result)

        with open(self.API_SCHEMAS_PATH + "/__init__.py", "w") as f:
            f.write(import_modules)

    def generate_api_endpoints(self):
        api_result = self._render(pkg_resources.resource_filename(__name__, "templates/api.tpl"),
                                          {
                                              "data": self.mechanic_obj["controllers"],
                                              "timestamp": datetime.datetime.utcnow()
                                          })

        with open(self.API_ENDPOINTS_PATH, "w") as f:
            f.write(api_result)

    def generate_controllers(self):
        import_modules = ""
        for namespace, namespace_obj in self.mechanic_obj["namespaces"].items():
            data = dict()
            for controller_key in namespace_obj["controllers"]:
                data[controller_key] = self.mechanic_obj["controllers"][controller_key]

            controllers_result = self._render(pkg_resources.resource_filename(__name__, "templates/controllers.tpl"),
                                              {
                                                  "data": data,
                                                  "models": namespace_obj["models"],
                                                  "schemas": namespace_obj["mschemas"],
                                                  "timestamp": datetime.datetime.utcnow()
                                              })

            controllers_output = self.API_CONTROLLERS_PATH + namespace
            if not os.path.exists(controllers_output):
                os.makedirs(controllers_output)

            import_modules = import_modules + "from controllers." + namespace + ".controllers import *\n"
            with open(controllers_output + "/__init__.py", "w"):
                pass

            with open(controllers_output + "/controllers.py", "w") as f:
                f.write(controllers_result)

        with open(self.API_CONTROLLERS_PATH + "/__init__.py", "w") as f:
            f.write(import_modules)

    def generate_starter_files(self,
                               all=False,
                               base=False,
                               app=False):
        """
        Only generate the absolute minimum files needed for a Flask app. At this point, no model, custom controllers, or
        marshmallow schemas exist yet, but you can run the app successfully.
        """
        if all:
            base = True
            app = True

        if app:
            shutil.copy(self.APP_RUN_SRC, self.APP_RUN_OUTPUT)
            shutil.copy(self.APP_INIT_SRC, self.APP_INIT_OUTPUT)
            shutil.copy(self.BASE_REQUIREMENTS_SRC, self.BASE_REQUIREMENTS_OUTPUT)
            shutil.copy(self.BASE_CONFIG_SRC, self.BASE_CONFIG_OUTPUT)
        if base:
            shutil.copy(self.BASE_INIT_SRC, self.BASE_INIT_OUTPUT)
            shutil.copy(self.BASE_CONTROLLERS_SRC, self.BASE_CONTROLLERS_OUTPUT)
            shutil.copy(self.BASE_SCHEMAS_SRC, self.BASE_SCHEMAS_OUTPUT)
            shutil.copy(self.BASE_FIELDS_SRC, self.BASE_FIELDS_OUTPUT)
            shutil.copy(self.BASE_EXCEPTIONS_SRC, self.BASE_EXCEPTIONS_OUTPUT)
            shutil.copy(self.BASE_DB_HELPER_SRC, self.BASE_DB_HELPER_OUTPUT)

    def _render(self, tpl_path, context):
        path, filename = os.path.split(tpl_path)
        return jinja2.Environment(loader=jinja2.FileSystemLoader(path or "./")).get_template(filename).render(context)

    def _deserialize_file(self):
        """
        Deserializes a file from either json or yaml and converts it to a dictionary structure to operate on.

        :param oapi_file:
        :return: dictionary representation of the OpenAPI file
        """
        if self.mechanic_file.endswith(".json"):
            with open(self.mechanic_file) as f:
                mechanic_obj = json.load(f)
        elif self.mechanic_file.endswith(".yaml") or self.mechanic_file.endswith(".yml"):
            with open(self.mechanic_file) as f:
                mechanic_obj = yaml.load(f)
        else:
            raise SyntaxError("File is not of correct format. Must be either json or yaml (and filename extension must "
                              "be one of those too).")
        self.root_dir = os.path.dirname(os.path.realpath(self.mechanic_file))
        return mechanic_obj

    def _copy_flask_app(self):
        pass

