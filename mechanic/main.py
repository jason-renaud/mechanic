"""mechanic code generator from an OpenAPI 3.0 specification file.

Usage:
    mechanic build <directory>
    mechanic merge <master> <files>...

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
from mechanic.src.compiler import Compiler
from mechanic.src.generator import Generator
from mechanic.src.merger import SpecMerger
from mechanic.src.reader import read_mechanicfile


def main():
    with open(pkg_resources.resource_filename(__name__, "VERSION")) as version_file:
        current_version = version_file.read().strip()

    args = docopt(__doc__, version=current_version)

    if args["build"]:
        directory = os.path.expanduser(args["<directory>"])
        filepath = directory + "/mechanic.json"
        try:
            mechanic_options = read_mechanicfile(filepath)
        except FileNotFoundError:
            filepath = directory + "/mechanic.yaml"
            mechanic_options = read_mechanicfile(filepath)
        compiler = Compiler(mechanic_options, mechanic_file_path=filepath)
        compiler.compile()
        Generator(directory, compiler.mech_obj, options=mechanic_options).generate()
    elif args["merge"]:
        files_to_merge = args["<files>"]
        spec_merger = SpecMerger(files_to_merge, args["<master>"])
        spec_merger.merge()

if __name__ == "__main__":
    main()
