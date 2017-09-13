"""mechanic code generator from an OpenAPI 3.0 specification file.

Usage:
    mechanic generate <oapi> <output> [--models --schemas --controllers --api --starter --merge=<merge-output>]

Arguments:
    oapi            OpenAPI 3.0 specification file
    output          The output directory for generated code

Options:
    -h --help           Show this screen
    -v --version        Show version
    -m, --models        Generate SQLAlchemy models
    -s, --schemas       Generate Marshmallow schemas
    -c, --controllers   Generate controllers to handle API endpoints
    -a, --api           Generate mapping of API endpoints to controllers
    -b, --starter       Generate starter files needed for a baseline Flask application
    -k, --merge=<merge-output>         Merges the OpenAPI spec if it is split into multiple files

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

    To generate a merged version of
"""
# native python
import os
import pkg_resources
from configparser import ConfigParser

# third party
from docopt import docopt

# project
from converter import Converter
from generator import Generator

cp = ConfigParser()
cp.read(pkg_resources.resource_filename(__name__, "../version.conf"))
current_version = cp.get("version", "current_version")


def main():
    args = docopt(__doc__, version=current_version)
    oapi_file = args["<oapi>"]
    output_dir = args["<output>"]

    all_objs = False
    models = args["--models"]
    schemas = args["--schemas"]
    controllers = args["--controllers"]
    api = args["--api"]
    starter = args["--starter"]
    merge = args["--merge"]

    # if not options are specified, generate all
    if not models and not schemas and not controllers and not api and not starter and not merge:
        all_objs = True

    Converter(oapi_file, "temp-mech.json").convert(merge=merge)
    Generator("temp-mech.json", output_dir).generate(all=all_objs,
                                                     models=models,
                                                     schemas=schemas,
                                                     controllers=controllers,
                                                     api=api,
                                                     starter=starter)
    os.remove("temp-mech.json")

if __name__ == "__main__":
    main()
