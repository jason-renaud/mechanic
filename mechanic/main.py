"""mechanic code generator from an OpenAPI 3.0 specification file.

Usage:
    mechanic generate <oapi> <output> [--models --schemas --controllers --api --starter --admin --exclude=<resource-type>...]

Arguments:
    oapi            OpenAPI 3.0 specification file
    output          The output directory for generated code

Options:
    -h --help                           Show this screen
    -v --version                        Show version
    -m, --models                        Generate SQLAlchemy models
    -s, --schemas                       Generate Marshmallow schemas
    -c, --controllers                   Generate controllers to handle API endpoints
    -a, --api                           Generate mapping of API endpoints to controllers
    -b, --starter                       Generate starter files needed for a baseline Flask application
    -f, --admin                         Generate Flask-Admin UI for all generated SQLAlchemy models

Examples:
    The following two commands are equivalent, and both generate all possible items:
        mechanic generate ~/my-oapi.yaml ~/my-proj
        mechanic generate ~/my-oapi.yaml ~/my-proj --models --schemas --controllers --api --starter

    To only generate SQLAlchemy models:
        mechanic generate ~/my-oapi.yaml ~/my-proj --models

    To only generate SQLAlchemy models AND Marshmallow schemas:
        mechanic generate ~/my-oapi.yaml ~/my-proj --models --schemas

    To only generate base files for a Flask app:
        mechanic generate ~/my-oapi.yaml ~/my-proj --starter

    To generate all resources and enable a Flask-Admin UI:
        mechanic generate ~/my-oapi.yaml ~/my-proj --admin
"""
# native python
import os
import pkg_resources

# third party
from docopt import docopt

# project
from mechanic.src.converter import Converter
from mechanic.src.generator import Generator


def main():
    with open(pkg_resources.resource_filename(__name__, "VERSION")) as version_file:
        current_version = version_file.read().strip()

    args = docopt(__doc__, version=current_version)
    oapi_file = args["<oapi>"]
    output_dir = args["<output>"]

    all_objs = False
    models = args["--models"]
    schemas = args["--schemas"]
    controllers = args["--controllers"]
    api = args["--api"]
    starter = args["--starter"]
    exclude = args["--exclude"]
    admin = args["--admin"]

    # if not options are specified, generate all
    if not models and not schemas and not controllers and not api and not starter:
        all_objs = True

    filename = "/home/zackschrag/fix-automator/fix/api/mechanic.yaml"
    Converter(oapi_file, filename).convert(merge=pkg_resources.resource_filename(__name__, "starter/app/static/docs.yaml"))
    Generator(filename, output_dir).generate(all=all_objs,
                                                     models=models,
                                                     schemas=schemas,
                                                     controllers=controllers,
                                                     api=api,
                                                     starter=starter,
                                                     exclude=exclude,
                                                     admin=admin)
    # os.remove(filename)

if __name__ == "__main__":
    main()
