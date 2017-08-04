### Summary
mechanic is a tool that can be used to generate code, from controller to database, with only an OpenAPI 3.0 specification file. Specifically, it generates code in Python 3.6, with these frameworks/tools:
- Flask-SQLAlchemy for the models generated (for the DB integration layer)
- Flask-Marshmallow for the schemas generated (for validation of input)
- Flask-RESTful for the controllers generated 

mechanic does 2 major things:
1) Convert OpenAPI 3.0 spec file into a format readable by mechanic templates
2) Generate code from the formatted file

#### Why not Swagger Codegen? ####
Swagger codegen appears to only generate starter code. It creates an API and validates input, but it stops after that. If the API changed, one would need to regenerate code, which would potentially overwrite code you had been developing over some time. From my understanding, swagger codegen is helpful for getting up and running in a new project, but it is not useful if your API is constantly changing and/or you need business logic to stay the same. There is also no integration with databases.

#### Who may find mechanic useful ####
1) Teams starting a brand new project with only a json specification file.
2) Developers who don't like copy and pasting code every time they have to create a new API.
3) You want to get up and running with working API code, but don't want to spend the time/effort of writing boilerplate code and selecting frameworks things up.

#### Who may not find mechanic useful ####
1) mechanic makes a lot of assumptions on frameworks and structuring things, so, for example, if you don't want to use sqlalchemy and marshmallow, this tool may not be for you.
2) If you are specific in how things are implemented, this tool may not be for you.
3) mechanic enforces some REST API 'best practices' in order to generate meaningful code. If you have an API that doesn't follow the enforced best practices outline below, this tool may not be for you.

### Install with pip
```bash
pip3 install mechanic-gen

# converts OpenAPI 3.0 spec file into mechanic format
mechanic convert path/to/openapi3.0/spec output/file/path

# generates code from mechanic file
mechanic generate output/file/path ~/<your-project-name> # <your-project-name> must NOT end with a "/", and is also used as the location in /etc to place the app.conf file.

# adds all of the starter files to your project that allow the project to be run
mechanic update-base ~/<your-project-name> --all

```
- Create **/etc/<your-project-name>/app.conf file with this text (fill out details specific to your project)
    - Dev is the only one needed to run the app immediately. Test is needed for running unit tests.
```bash
[database]
dev:     postgresql://USERNAME:PASSWORD@HOSTNAME:5432/DB_NAME
test:    postgresql://USERNAME:PASSWORD@HOSTNAME:5432/DB_NAME

[server]
port: 5000
```
- Run your app
```bash
cd ~/<your-project-name>
pip3 install -r requirements.txt
python run.py
```

### Starting from source code
- Clone the mechanic repo first, then execute these commands:
```bash
virtualenv -p python3.6 path/to/virtualenv
source path/to/virtualenv/bin/activate
cd ~/mechanic/

python mechanic.py generate examples/petstore-mechanic.json ~/petstore # Note the last segment of the directory path (in this case 'petstore') is considered the location where the app.conf file will exist. Therefore, the app.conf file MUST be located /etc/<app-name>/app.conf, in this case /etc/petstore/app.conf

mkdir /etc/petstore
cp ~/petstore/app/conf/app.conf /etc/petstore/
```
- Now edit /etc/petstore/app.conf and update DB urls and port fields
- Next install pip requirements
```bash
cd ~/petstore
pip3 install -r requirements.txt
python run.py
```
- You should see an exception with this in it: 
```bash
ModuleNotFoundError: No module named 'services'
```
- This means we still need to create the business logic pieces, aka 'services'. For now, they can be stubs.
- Create the file (create directories too) services/store/services.py: 
```python
from base.services import BaseService


class PetService(BaseService):
    pass
```
- Before running again, verify the 'dev' DB specified in /etc/petstore/app.conf exists.
```bash
export FLASK_CONFIG=development
python run.py
```
- Now you will see an error similar this:
```bash
sqlalchemy.exc.ProgrammingError: (psycopg2.ProgrammingError) schema "store" does not exist
LINE 2: CREATE TABLE store.pets (
```
- We need to create the schemas in the database for each 'namespace', in this case 'store'. 
- Once you have created the schema 'store' in your database, try running again
```bash
python run.py
```
- This time it should succeed, and you should have a fully functioning API. Try doing some REST calls to test it out.

### REST API best practices enforced by mechanic
#### mechanic types of APIs
mechanic supports 3 types of APIs - Collection, Command, and Item.

#### Endpoint definitions 
An API that represents a resource should have 2 endpoints, 1) an endpoint to the collection of these resources and 2) an endpoint to access/update a single item of this resource.  Examples: let's say you have an endpoint to represent dogs, you might have these 2 endpoints: 
- /cars/wheels/ - this represents a collection of all of the resource wheels 
- /cars/wheels/{id} - where {id} is the identifier of the wheel

An API that represents a command to execute on a resource should be of the format [path/to/resource/{id}]/\<command>. Here are a few examples:
- /cars/wheels/4/replace - in this case, "replace" is the command, and the wheel with id 4 is the resource being operated on. 
- /cars/engine/1/start - "start" is the command, and the engine with id 1 is the resource being operated on.

Assumptions:
The last part of the path segment before '{id}' or 'all' is always the resource name.
- /cars/wheels/{id}/rotate - 'wheels' is the resource. The controller will therefore be named "WheelRotateCommandController", and the service class "WheelRotateService"
- /cars/wheels/{id}/remove-tire - The controller will be named "WheelRemovetireCommandController", and the service class "WheelRemovetireService"
- /cars/wheels/{id} - The controller will be named "WheelController"
- /cars/wheels - The controller will be named "WheelCollectionController"

In a command API, it is assumed the parameters being passed in are from a schema (to be validated), and the response being returned is another schema that is saved in the DB. Therefore, the schema defined in the 'responses' object in the OAPI spec file will have both a marshmallow schema defined AND a SQLAlchemy model defined. However, the schema defined in 'requestBody' will ONLY have a schema defined, and the request body is NOT saved in the DB and therefore has no SQLAlchemy model defined.

#### Model definitions
- mechanic automatically uses the field "identifier" as the primary key of the resource, which is also the id to use in the url when retrieving an object. DO NOT define an "id" or "identifier" field in your schema properties in the specification file.
- mechanic automatically defines foreign key relationships whenever a schema of type "array" with a reference to another schema is used.
- mechanic needs an "x-mechanic-namespace" extension to be defined for each path object in the OAPI spec file. See examples/petstore-oapi3.json for an example. This value is used as the "schema" attribute in the SQLAlchemy model.

#### mechanic OpenAPI 3.0 extensions and additional syntax requirements
| extension                 | description |
| ---------                 | ----------- |
| x-mechanic-namespace      | A way to separate categories of APIs. This is used to determine which packages to separate code into. This can also be placed on a schema object, although it is only needed if a schema is referenced by another schema outside of it's namespace. |
| x-mechanic-plural         | mechanic uses a library called 'inflect' to automatically determine plural and singular forms of words. However it doesn't always work as needed, so you can use this attribute to override the plural form of the schema name. |
| x-mechanic-external-resource | A way to mark a server url as an external url to retrieve a resource. Used in command APIs, where the url to get the needed resource lives on another server. |
| x-mechanic-backref        | On a property object. Override the default name for SQLAlchemy backref. This is typically only needed if you have multiple attributes in a schema that reference the same schema. For example, if you had a schema Person, with attributes 'cars' and 'primaryCar', that each referenced a Car schema. |  
| *x-mechanic-async         | Specify if you want this method to return asynchronously
*not supported yet but in progress

- MUST have "title" defined for each schema object
- MUST have x-mechanic-namespace defined for each path object
- 'openapi' version MUST be '3' or greater
- Each path method MUST have a '200', '201', '202', or '204' response object defined.
- Schema objects MUST have properties defined at the top level. I.e., allOf, anyOf, etc. are not supported at this time.
- The path uri MUST be of one of these formats: /uri/to/resource/, /uri/to/resource/{id}, or /uri/to/resource/{id}/<command>
- mechanic currently only supports the following HTTP methods:
    - get
    - put
    - post
    - delete

#### mechanic does NOT support
- allOf, anyOf, etc. For a schema - the properties object MUST be defined
- mechanic does not run from the servers url(s), however it does use them as the base resource url for command APIs.
- < Python 3.6, generated code is Python 3.6
- security definitions
- YAML, mechanic only supports json
- Query parameters are not supported except for GET on collection resources. You add custom query parameters besides the default supported ones.
- consumes/produces, assumes only json

### Future improvement ideas
- Add support for 'embed' query parameter to display the full resource or show it's uri reference instead.
- Add support for overriding generated code.
    - Add meta tag in schema itself? Add param in cli? Annotation at file level?
- x-mechanic-async extension - define if a REST method returns asynchronously.
- Many-to-many relationships between models/schemas
- enum properties