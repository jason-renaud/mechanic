"""mechanic code generator from an OpenAPI 3.0 specification file.

Usage:
    mechanic build <directory>
    mechanic merge <master> <files>...
    mechanic generate (model|schema|controller|versions) <object_path> <output_file> [--filter-tag=<tag>...] [--exclude-tag=<tag>...]

Note:
    - 'mechanic generate' is experimental, use with caution

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
from mechanic.src.compiler import Compiler, Merger, MECHANIC_SUPPORTED_HTTP_METHODS
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
            os.remove('temp.yaml')

            oapi_obj = merger.oapi_obj
            oapi_version = oapi_obj.get('info', {}).get('version', '0.0.1')

            filter_tags = args['--filter-tag']
            exclude_tags = args['--exclude-tag']

            filter_tag_set = set(args['--filter-tag'])
            exclude_tag_set = set(args['--exclude-tag'])

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

                    if not exclude_tag_set.intersection(s2) and filter_tag_set <= s2 or len(filter_tags) == 0:
                        if oapi_obj['components']['schemas'][model_name].get('x-mechanic-model-generate'):
                            context['codeblocks'].append({
                                'type': 'model',
                                'class_name': oapi_obj['components']['schemas'][model_name].get('x-mechanic-model', model_name),
                                'base_class_name': 'MechanicBaseModelMixin',
                                'version': oapi_obj['components']['schemas'][model_name].get('x-mechanic-version',
                                                                                             oapi_version),
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

                    if not exclude_tag_set.intersection(s2) and filter_tag_set <= s2 or len(
                            filter_tags) == 0:
                        context['codeblocks'].append({
                            'type': 'schema',
                            'class_name': oapi_obj['components']['schemas'][model_name].get('x-mechanic-schema-name',
                                                                                            model_name + 'Schema'),
                            'base_class_name': 'MechanicBaseModelSchema',
                            'version': oapi_obj['components']['schemas'][model_name].get('x-mechanic-version',
                                                                                         oapi_version),
                            'oapi': oapi_obj['components']['schemas'][model_name],
                        })
            elif args['controller']:
                for path_name, path in oapi_obj['paths'].items():
                    if path.get('x-mechanic-controller'):
                        model = path.get('x-mechanic-controller').get('model')
                        schema = path.get('x-mechanic-controller').get('schema')
                        path_version = path.get('x-mechanic-version', oapi_version)

                        if not oapi_obj['paths'][path_name]['x-mechanic-controller'].get('responses'):
                            oapi_obj['paths'][path_name]['x-mechanic-controller']['responses'] = dict()
                        if not oapi_obj['paths'][path_name]['x-mechanic-controller'].get('requests'):
                            oapi_obj['paths'][path_name]['x-mechanic-controller']['requests'] = dict()
                        oapi_responses = oapi_obj['paths'][path_name]['x-mechanic-controller']['responses']
                        oapi_requests = oapi_obj['paths'][path_name]['x-mechanic-controller']['requests']

                        for method_name, method in path.items():
                            if method_name in MECHANIC_SUPPORTED_HTTP_METHODS:
                                if not oapi_responses.get(method_name):
                                    oapi_responses[method_name] = dict()

                                oapi_responses[method_name]['model'] = model
                                oapi_responses[method_name]['schema'] = schema

                                for response_code, response_obj in method.get('responses', {}).items():
                                    if response_code.startswith('2'):
                                        oapi_responses[method_name]['code'] = response_code

                                if method.get('requestBody'):
                                    if not oapi_requests.get(method_name):
                                        oapi_requests[method_name] = dict()

                                    oapi_requests[method_name]['model'] = model
                                    oapi_requests[method_name]['schema'] = schema

                        context['codeblocks'].append({
                            'type': 'controller',
                            'class_name': path['x-mechanic-controller']['class_name'],
                            'base_class_name': path['x-mechanic-controller']['base_class_name'],
                            'version': path.get('x-mechanic-version', oapi_version),
                            'oapi': oapi_obj['paths'][path_name],
                        })
            elif args['versions']:
                controllers = []

                for path_name, path in oapi_obj['paths'].items():
                    if path.get('x-mechanic-controller'):
                        controllers.append(path['x-mechanic-controller'])

                context['codeblocks'].append({
                    'type': 'versions',
                    'controllers': controllers,
                    'version': path.get('x-mechanic-version', oapi_version),
                    'oapi': oapi_obj['paths'][path_name],
                })

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
