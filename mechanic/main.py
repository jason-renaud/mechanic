"""mechanic code generator from an OpenAPI 3.0 specification file.

Usage:
    mechanic build <directory>
    mechanic merge <master> <files>...
    mechanic generate (model|schema|controller) <object_path> <output_file> [--filter-tag=<tag>...]

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
import datetime

# third party
from docopt import docopt

# project
from mechanic.src.compiler import Compiler, Merger
from mechanic.src.generator import Generator
from mechanic.src.merger import SpecMerger
from mechanic.src.reader import read_mechanicfile


def _render(tpl_path, context):
    path, filename = os.path.split(tpl_path)
    import jinja2
    return jinja2.Environment(loader=jinja2.FileSystemLoader(path or './')).get_template(filename).render(
        context)


def main():
    with open(pkg_resources.resource_filename(__name__, 'VERSION')) as version_file:
        current_version = version_file.read().strip()

    args = docopt(__doc__, version=current_version)

    if args['build']:
        directory = os.path.expanduser(args['<directory>'])
        filepath = directory + '/mechanic.json'
        try:
            mechanic_options = read_mechanicfile(filepath)
        except FileNotFoundError:
            filepath = directory + '/mechanic.yaml'
            mechanic_options = read_mechanicfile(filepath)
        compiler = Compiler(mechanic_options, mechanic_file_path=filepath)
        compiler.compile()
        Generator(directory, compiler.mech_obj, options=mechanic_options).generate()
    elif args['merge']:
        files_to_merge = args['<files>']
        spec_merger = SpecMerger(files_to_merge, args['<master>'])
        spec_merger.merge()
    elif args['generate']:
        context = {
            'timestamp': datetime.datetime.utcnow(),
            'codeblocks': []
        }
        # if object_path is file, generate all of 'type' (e.g. 'model', 'schema', 'controller')
        if args['<object_path>'].endswith('.yaml') \
                or args['<object_path>'].endswith('.yml') \
                or args['<object_path>'].endswith('.json'):
            # merge oapi file
            oapi_file = args['<object_path>']
            merger = Merger(oapi_file, 'temp.yaml')
            merger.merge()
            oapi_obj = merger.oapi_obj


            print(args)
            filter_tags = args['--filter-tag']
            s1 = set(args['--filter-tag'])
            if args['model']:
                # first generate any additional tables from components.x-mechanic-db-tables
                for table_name, table_def in oapi_obj['components'].get('x-mechanic-db-tables', {}).items():
                    context['codeblocks'].append({
                        'type': 'table',
                        'table_name': table_name,
                        'oapi': oapi_obj['components']['x-mechanic-db-tables'][table_name]
                    })

                # next generate models from components.schemas
                for model_name, model in oapi_obj['components']['schemas'].items():
                    # get tags for filtering code generation
                    s2 = set(model.get('x-mechanic-tags', []))

                    if s1.intersection(s2) or len(filter_tags) == 0:
                        context['codeblocks'].append({
                            'type': 'model',
                            'class_name': model_name,
                            'base_class_name': 'MechanicBaseModelMixin',
                            'oapi': oapi_obj['components']['schemas'][model_name],
                        })
            elif args['schema']:
                for model_name, model in oapi_obj['components']['schemas'].items():
                    # add sane defaults
                    if not model.get('x-mechanic-model'):
                        if model.get('x-mechanic-db'):
                            oapi_obj['components']['schemas'][model_name]['x-mechanic-model'] = model_name
                    # TODO add more defaults here as needed

                    s2 = set(model.get('x-mechanic-tags', []))

                    if s1.intersection(s2) or len(filter_tags) == 0:
                        context['codeblocks'].append({
                            'type': 'schema',
                            'class_name': model_name + 'Schema',
                            'base_class_name': 'MechanicBaseModelSchema',
                            'oapi': oapi_obj['components']['schemas'][model_name],
                        })
            elif args['controller']:
                pass

        # if object_path is oapi object, generate for 'type'
        result = _render(pkg_resources.resource_filename(__name__, 'templates/code.tpl'), context=context)
        # print(result)
        # with open(args['<output_file>'], 'w') as f:
        #     f.write(result)

        mechanic_save_block = None
        try:
            with open(args['<output_file>'], 'r') as f:
                current_contents = f.read()
                if len(current_contents.split('# END mechanic save #')) >= 2:
                    mechanic_save_block = current_contents.split('# END mechanic save #')[0]
        except FileNotFoundError:
            # file doesn't exist, create it below
            pass

        with open(args['<output_file>'], 'w') as f:
            if not mechanic_save_block:
                f.write(result)
            else:
                f.write(mechanic_save_block)
                mechanic_modify_block = result.split('# END mechanic save #')[1]
                f.write('# END mechanic save #')
                f.write(mechanic_modify_block)


if __name__ == '__main__':
    main()
