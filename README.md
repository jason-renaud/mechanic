# mechanic

Generates code for Flask-RESTful controllers, Flask-SQLAlchemy models, and Flask-Marshmallow schemas, so that an API can be created immediately.

#### Why not Swagger Codegen? ####
Swagger codegen appears to only generate starter code. It creates an API and validates input, but it stops after that. If the API changed, one would need to regenerate code, which would potentially overwrite code you had been developing over some time. From my understanding, swagger codegen is helpful for getting up and running in a new project, but it is not useful if your API is constantly changing, but you need business logic to stay the same. There is also no integration with databases.

#### Who may find mechanic useful ####
1) Teams starting a brand new project with only a json specification file.
2) Developers who don't like copy and pasting code every time they have to create a new API.
3) You want to get up and running with working API code, but don't want to spend the time/effort of setting things up.

#### Who may not find mechanic useful ####
1) mechanic makes a lot of assumptions on frameworks and structuring things, so if you don't want to use sqlalchemy and marshmallow, this tool is not for you.
2) If you are specific in how things are implemented, you may not enjoy this tool.

#### Things to note
- OpenAPI 3.0 is tentatively supported, as final spec has not been released yet.
- Assumes 'tags' field in OAPI "paths" are used as folder dividers. Exactly one tag MUST be defined with the format "x-faction-namespace=your-package-name". For example "x-faction-namespace=storage". The python package name will be "storage". This also becomes the database schema name.
- Requires 2xx responses to be defined for each endpoint/path
- Only generates models referenced from endpoints, not necessarily all models defined in OpenAPI definitions section. If, for example, you have a defined an ABC model in "definitions" in the spec file, but that model is not referenced directly/indirectly from any endpoint, it will not generate code for that model. 
- If you want camel caps for a model name, property name, etc., you need to define things with a dash. E.g., storage-device will be StorageDevice, but storagedevice will just be Storagedevice
- mechanic automatically appends Model, Schema, Controller, and Service to the name of your models that are defined in #/definitions. When naming your models, don't add "Model" to the end of the name otherwise it will display as StorageDeviceModelModel instead of just StorageDeviceModel.
- mechanic only supports GET, PUT, POST, DELETE at the moment. There are plans to support PATCH.
- generate-resources.py will NOT overwrite your services files. This is where your business logic lives. You can run this script as many times as you want as your API spec changes.
- The "title" attribute of each model defined in the "definitions" section of the api spec is what is used as the resource name.

#### mechanic does NOT support ####
- Query parameters (work in progress)
- Security definitions
- consumes/produces, assumes only json
- "host" in spec file. mechanic simply runs the flask dev server on port 5000, by default
- < Python 3.6, generated code is Python 3.6


#### Set Up
- Clone the repo first, then execute these commands:
```bash
virtualenv -p python3.6 path/to/virtualenv
source path/to/virtualenv/bin/activate
cd ~/mechanic/
mkdir ~/your-project-name

# generate-starter-files.py should only be run one time
python generate-starter-files.py ~/your-project-name

mkdir /etc/your-project-name
cp ~/your-project-name/app/conf/app.conf /etc/your-project-name/
# after copying the conf file, edit it to setup your DB urls

# install pip requirements
cd ~/your-project-name
pip3 install -r requirements.txt
cd ~/mechanic

# generate-resources.py can be run any time as your API spec changes
python generate-resources-v3.py path/to/openapi.json path/to/project/dir
```
- Create services with correct names. Create a file services/your-package-name/services.py You can use this as an example to get something working (obviously, change "StorageDevice" to whatever  name of your resource is. It needs to match the resource name defined in models/controllers/schemas):

```python
from base.services import BaseService


class StorageDeviceService(BaseService):
    pass
```
- Create a database schema for each namespace tag name you have defined. E.g., if you have a path with a tag "x-faction-namespace=storage", create the database schema "storage" in your DB.
```bash
cd path/to/project/dir
python run.py /etc/your-project-name/app.conf
```
- Test the API using the REST client of your choice (I like Postman: https://www.getpostman.com/)

#### generate-starter-files.py ####
```bash
python generate-starter-files.py [OPTIONS] path/to/project/dir
```
Options:
- --force       Deletes directories and regenerates all code as if a new project was created.
- --base-only   Deletes base/ directory and regenerates all code in it as if a new project was created. Useful if upgrades have been made to base classes in mechanic, and you want to pick up the latest code.
- --app-only    Deletes app/ directory and regenerates all code in it as if a new project was created. 
- --tests-only  Deletes tests/ directory and regenerates all code in it as if a new project was created.

#### generate-resources-v3.py ####
```bash
python generate-resources-v3.py [OPTIONS] path/to/openapi/spec.json path/to/project/dir
```
Options:
- --debug       Instead of generating files, creates a file with the formatted data used by the templates to generate new files.

#### Future improvements/known issues
- Implement support for OAPI 3.0.
- Add support for links between resources instead of just foreign key ids.
- Separate file json schemas 
- Remove camel case dash thing
- Add support for overriding generated code 
    - Add meta tag in schema itself? Add param in cli? Annotation at file level?
- Only call service methods if they exist OR determine if method exists, and if not use base method.
- Add task resource to all methods with a collection of running tasks
- Decide best way to return tasks for sync/async completion (PATCH, POST?, DELETE)
- Only return tasks for async methods?
- Need a way to define if a method is sync/async, maybe in the json schema?
- Figure out many-to-many relationships in codegen
- Gitflow http://nvie.com/posts/a-successful-git-branching-model/
- Add support for query parameters
