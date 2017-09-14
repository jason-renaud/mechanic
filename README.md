### Summary
mechanic is a tool that can be used to generate code, from controller to database, with only an OpenAPI 3.0 specification file. Specifically, it generates code in Python 3.6, with these frameworks/tools:
- Flask-SQLAlchemy for the models generated (for the DB integration layer)
- Flask-Marshmallow for the schemas generated (for validation of input)
- Flask-RESTful for the controllers generated 

#### Why not Swagger Codegen? ####
tldr: Swagger codegen allows for more flexibility in how you implement your API, while mechanic allows for rapid development of a constantly changing API.

Swagger codegen appears to only generate starter code. It creates an API and validates input, but it stops after that. If the API changed, one would need to regenerate code, which would potentially overwrite code you had been developing over some time. From my understanding, swagger codegen is helpful for getting up and running in a new project, but it is not useful if your API is constantly changing and/or you need business logic to stay the same. There is also no integration with databases. Because Swagger codegen focuses on getting the base of an API working, you have more flexibility in how you implement your API. On the other hand, mechanic is very opinionated, but it allows you to go from zero-to-fully functioning API very quickly. 

#### Who may find mechanic useful ####
1) Teams starting a brand new project with only a OpenAPI 3.0 specification file.
2) Developers who don't like copy and pasting code every time they have to create a new API endpoint.
3) You want to get up and running with working API code, but don't want to spend the time/effort of writing boilerplate code and selecting frameworks.
4) You have a constantly evolving API and don't want to consistently rewrite code to, for example, change or remove a single attribute on a resource.

#### Who may not find mechanic useful ####
1) mechanic makes a lot of assumptions on frameworks and structuring things, so, for example, if you don't want to use sqlalchemy and marshmallow, this tool may not be for you.
2) If you are specific in how things are implemented, this tool may not be for you.
3) mechanic enforces some REST API 'best practices' in order to generate meaningful code. If you have an API that doesn't follow the enforced best practices outline below, this tool may not be for you.

### Getting started
##### Install with pip
```bash
pip3 install mechanic-gen

# converts OpenAPI 3.0 spec file into mechanic format
mechanic generate ~/my-oapi.yaml ~/my-proj
```
- Set the necessary environment variables (Note that <db-type> can theoretically work with any SQL db that SQLAlchemy supports, but mechanic has only been tested with 'postgresql'):
```bash
export FLASK_CONFIG=development
export MECHANIC_DEV_DATABASE=<db-type>://USERNAME:PASSWORD@HOSTNAME:5432/DB_NAME
export MECHANIC_TEST_DATABASE=postgresql://postgres:postgres@127.0.0.1:5432/<your-test-db-name>
```
- (Optional) Create a virtualenv for your project
```bash
virtualenv -p python3.6 path/to/virtualenv
source path/to/virtualenv/bin/activate
```
- Run your app
```bash

cd ~/<your-project-name>
pip3 install -r requirements.txt
python run.py
```

##### Starting from source code
- Clone the mechanic repo first, then execute these commands:
```bash
virtualenv -p python3.6 path/to/virtualenv
source path/to/virtualenv/bin/activate
cd path/to/cloned/repo/mechanic/

python main.py generate ~/my-openapi-spec.yaml ~/my-proj
```

- Next install pip requirements
```bash
cd ~/petstore
pip3 install -r requirements.txt
python run.py
```

##### Common errors during setup
- Make sure your database has the schemas created for each namespace that is defined. If you did not define any 
namespaces for your resources, create a schema named "default".
- mechanic should provide informative error messages if something has gone wrong. If it does not and you think it 
should, submit an issue.
- First place your OpenAPI 3.0 spec file in the Swagger Editor online and make sure it is a valid specification. 

### REST API best practices enforced by mechanic
##### mechanic types of APIs
mechanic supports 2 types of APIs - Collection, and Item. If the endpoint uri does not match one of these patterns, there
will be no base implementation for the controller. If there is more than one controller for a certain resource that 
does not match one of these API patterns, then starting with the second controller, an incrementing number will be 
appended to the end of the controller name. For example, let's say you have 4 endpoints defined like this:

1) /cars/wheels
2) /cars/wheels/{id}
3) /cars/wheels/{id}/rotate/{rotate-id}
4) /cars/wheels/{id}/replace

\#1 will be mapped as an Item controller, \#2 will be mapped as a Collection controller, \#3 and \#4 do not match an Item
or Collection pattern, so they will be named WheelController and WheelController0 (depending on which one if processed
first in mechanic). If there was a third non-Item and non-Collection controller for wheels, it would be named 
WheelController1. Because these controllers are non-Item and non-Collection, they have to be extended to be used. See 
[here](#what-if-i-want-to-change-the-behavior-of-a-generated-controller) for more details on extending controllers.

##### Endpoint definitions 
An API that represents a resource should have 2 endpoints, 1) an endpoint to the collection of these resources and 2) an 
endpoint to access/update a single item of this resource.  Examples: let's say you have an endpoint to represent dogs, 
you might have these 2 endpoints: 
- /cars/wheels/ - this represents a collection of all of the resource wheels 
- /cars/wheels/{id} - where {id} is the identifier of the wheel

Assumptions:
The last part of the path segment before '{id}' is always the resource name, or the last part of the uri segments. In 
both of the examples below, "Wheel" is the resource.
- /cars/wheels/{id} - The controller will be named "WheelItemController"
- /cars/wheels - The controller will be named "WheelCollectionController"

Let's say you have an endpoint definition that looks like this: **/cars/{id}/wheels/{wheel_id}**  
  
This is allowed, but mechanic will just not provide base functionality in a controller for you. The 
generated controller will extend BaseController, and then in order to add functionality you need to extend that 
generated class. See [here](#what-if-i-want-to-change-the-behavior-of-a-generated-controller) for more details on 
extending controllers.

##### Model definitions
- mechanic automatically uses the field "identifier" as the primary key of the resource, which is also the id to use in 
the url when retrieving an object. DO NOT define an "id" or "identifier" field in your schema properties in the 
specification file.
- mechanic automatically defines foreign key relationships whenever a schema of type "array" with a reference to another
schema is used.

##### mechanic OpenAPI 3.0 extensions and additional syntax requirements
| extension                 | description |
| ---------                 | ----------- |
| x-mechanic-namespace      | A way to separate categories of APIs. This is used to determine which packages to separate code into. This can also be placed on a schema object, although it is only needed if a schema is referenced by another schema outside of it's namespace. |
| x-mechanic-plural         | mechanic uses a library called 'inflect' to automatically determine plural and singular forms of words. However it doesn't always work as needed, so you can use this attribute to override the plural form of the schema name. |

- In order to name a model/schema differently from it's key in the OpenAPI schema, simply define the 'title' attribute.
- 'openapi' version MUST be '3' or greater
- Each path method MUST have a '200', '201', '202', or '204' response object defined.
- The path uri MUST be of one of these formats: /uri/to/resource/, /uri/to/resource/{id}, or 
/uri/to/resource/{id}/<command>
- mechanic currently only supports the following HTTP methods:
    - get
    - put
    - post
    - delete

##### mechanic environment variables
| extension                 | description |
| ---------                 | ----------- |
| FLASK_CONFIG              | Must be set to either 'development', 'testing', or 'production' |
| FLASK_PORT                | Defaults to 5000 if not set |
| MECHANIC_DEV_DATABASE     | Url of the development db, used when FLASK_CONFIG is set to 'development' |
| MECHANIC_TEST_DATABASE    | Url of the test db, used when FLASK_CONFIG is set to 'testing' |
| MECHANIC_PRO_DATABASE     | Url of the production db, used when FLASK_CONFIG is set to 'production' |

##### mechanic does NOT support
- mechanic does not run from the servers url(s), however it does use them as the base resource url for command APIs.
- less than Python 3.6, generated code is Python 3.6
- security definitions
- Query parameters are not supported except for GET on collection resources.
- consumes/produces, assumes only json

### FAQ
##### What if my OpenAPI file is split across many files?
mechanic automatically merges your OpenAPI file if it is split in a particluar way. External references much be relative
to the OpenAPI main file, and mechanic currently does not support external references that are located on a different 
filesystem. For example, let's say your directory structure looks like this:
```bash
~/oapi/
    master-oapi.yaml
    transportation/
        car.yaml
        airplane.yaml
        pilot.yaml
```
In master-oapi.yaml, the reference to airplane.yaml must look like this:
```yaml
$ref: transportation/airplane.yaml#/Airplane
```
And the contents of airplane.yaml might look like this:
```yaml
Airplane:
    type: object
    properties:
      name:
        type: string
      airline:
        type: string
      pilot:
        $ref: transportation/pilot.yaml#/Pilot
```
**Important**: notice that in airplane.yaml, the reference to pilot is still relative to master-oapi.yaml, NOT relative 
to airplane.yaml.

Since your specification is split across many files, you may have had difficulties generating documentation for your 
specification. If you want to generate the merged file, you can simply run this command:
 ```bash
 # ~/my-dir doesn't do anything in this case, because adding the --merge flag without any other flags indicates to only 
 # generate the merged file, but no other code
 mechanic generate ~/master-oapi.yaml ~/my-dir --merge=merged-file.yaml
 ```
Now you have a merged file that you can put into other tools (such as Swagger UI) to generate your documentation.

##### What if I want to change the behavior of a generated controller?
mechanic was designed (or at least attempted) in such a way to allow you to customize behavior to suit your needs. 
Let's say mechanic generated a controller called AirplaneController that maps to endpoint /api/airplanes/{id}. Add a new 
file (it can be named anything you want) within the same directory as where AirplaneController is defined (NOT the same 
file! This would get overwritten). The directory structure would look like this:
```bash
~/my-proj/
    app/..
    base/..
    controllers/
        default/
            controllers.py
            my_custom_controllers.py
```
And then within my_custom_controllers.py, you can declare your controller class and extend AirplaneController. Take a 
look at the base/controllers.py class to determine how you might want to extend the controller and customize the 
behavior. mechanic will look through the inheritance hierarchy to find the leaf class (the class that has no 
subclasses), and then map the endpoint to that class instead of the auto-generated class.

Let's say my_custom_controllers.py has this code:
```python
from .controllers import AirplaneController


class MyCustomAirplaneController(AirplaneController):
    def get(self, resource_id):
        return "airplane taking off"
```
If you execute a GET /api/airplanes/{id} request, you will get the response "airplane taking off" instead of the
generated response in AirplaneController. You might want to take a look at base/controllers.py and see what methods are
defined and in what order they are executed. Then you can override the methods that will fit your needs the best.

**Important**: After you have created a new file (in this case my_custom_controllers.py), you MUST regenerate your code. 
This is so that mechanic can pick up the new file and add the imports appropriately. But if you are defining a new class 
within the file and it already exists, there is no need to regenerate the code.


