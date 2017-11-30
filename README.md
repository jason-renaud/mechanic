### Summary
mechanic is a "toolkit" for building an API in Python from an OpenAPI 3.0 specification file. It (at least partially) 
bridges the gap between the contract (the API spec) and the enforcement of that contract (the code). 

mechanic was created because swagger codegen did not sufficiently meet our code generation needs. Our biggest 2 
requirements were:
- Ability to generate server stubs without overriding existing code/business logic.
- Generate DB models and serialization/deserialization from the OpenAPi 3.0 spec.

#### What does it do?
- Generates SQLAlchemy Models and Marshmallow schemas.
- Generates API endpoint controllers associated with the models and schemas.
- Generates Flask starter code that gets you from zero to fully functioning API in seconds.
- Customize how the files are generated (naming patterns, location) using a mechanic.yaml/.json file.
- Adds some useful extensions to the OpenAPI 3.0 spec.

Think of the API specification file as defining the WHAT: the code to be generated. The mechanic file defines the HOW:  
the way in which the code is generated (things that don't necessarily affect the contract being enforced).

#### Why not Swagger Codegen?
tldr: Swagger codegen allows for more flexibility in how you implement your API, while mechanic allows for rapid 
development of a constantly changing API.

1) At the time of this writing, Swagger codegen does not support OpenAPI 3.0 server stubs.
2) From my understanding/experience with it, swagger codegen only generates starter code. I.e. it creates an API and 
validates input, but it stops after that. If the API changed, one would need to regenerate code, which would potentially 
overwrite code you had been developing over some time. Swagger codegen is helpful for getting up and running in a new 
project, but it falls short if your API is constantly changing and/or you need existing business logic to not get 
overwritten when generating new stubs. 
3) There is no integration with databases. Again, swagger codegen's focus is generating stubs to get you started, which
might be all you need. However, mechanic makes some assumptions (with the ability to customize) on how models will be
related (e.g., foreign keys). 

Because Swagger codegen focuses on getting the base of an API working, you have a little more flexibility in how you 
implement your API. On the other hand, mechanic is very opinionated, but it allows you to go from zero-to-fully 
functioning API very quickly. 

#### Who may find mechanic useful
1) Teams starting a brand new project with only a OpenAPI 3.0 specification file.
2) Developers who don't like copy and pasting code every time they have to create a new API endpoint.
3) You want to get up and running with working API code, but don't want to spend the time/effort of writing boilerplate 
code and selecting frameworks.
4) You have a constantly evolving API and don't want to consistently rewrite code to, for example, change or remove a 
single attribute on a resource.

#### Who may not find mechanic useful
1) mechanic makes a lot of assumptions. So, for example, if you don't want to use SQLAlchemy and Marshmallow, this tool 
may not be for you.
2) If you want to craft each resource representation in code, this tool may not be for you.
3) If your API is relatively stable without much risk for changing, this tool may not be for you.
4) If you have a lot of API endpoints that don't necessarily map directly to a resource, this tool may not be for you.

### Getting started
#### Install with pip
- (Optional) Create a virtualenv for your project
```bash
virtualenv -p python3.6 path/to/virtualenv
source path/to/virtualenv/bin/activate
```
- Install mechanic
```bash
pip install mechanic-gen
```
- Create a mechanic.yaml in the directory you want the code to be generated in, with these contents:
```yaml
OPENAPI: <path>/<to>/<openapi-spec-file>.yaml # path is relative to the mechanic.yaml file. 
APP_NAME: myappname
DATABASE_URL: "your db url" # example: postgresql://postgres:postgres@127.0.0.1:5432/dev
```
- IMPORTANT: Make sure your database has a schema (i.e. 'schema' in the Postgres sense of the word) defined called 
'default' (or for each unique usage of **x-mechanic-namespace**).
- **Note**: the database url can theoretically work with any SQL db that SQLAlchemy 
supports, but mechanic has only been tested with postgres.  
```bash
cd <directory with mechanic.yaml file>
mechanic build . # this generates the code
pip install -r requirements.txt
python run.py
```
You should now have a fully functioning API. Execute a REST call at http://127.0.0.1:5000/api/<your-resource> to see it 
action. Next, see [mechanic file reference](docs/mechanicfile-reference.md) for details on customizing how the app is 
generated.
