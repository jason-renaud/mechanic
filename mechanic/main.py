"""mechanic code generator from an OpenAPI 3.0 specification file.

Usage:
    mechanic build <directory>

Arguments:
    directory                           Directory that has the mechanicfile

Options:
    -h --help                           Show this screen
    -v --version                        Show version

Examples:
    mechanic build .
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

    with open(args["<directory>"] + "/mechanicfile") as f:
        print(f.read())

if __name__ == "__main__":
    main()
