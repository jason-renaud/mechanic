# Tugboat Code Generation

#### Assumptions
- Only support Swagger 2.0 (json only) at the moment, with work underway to support OpenAPI 3.0.
- Assumes 'tags' field in OAPI "paths" are used as folder dividers. Exactly one tag MUST be defined with the format "x-faction-namespace=your-package-name". For example "x-faction-namespace=storage". The python package name will be "storage". This also becomes the database schema name.
- Requires 2xx responses to be defined for each endpoint/path
- Only generates models referenced from endpoints, not necessarily all models defined in OpenAPI definitions section. If, for example, you have a defined an ABC model in "definitions" in the spec file, but that model is not referenced directly/indirectly from any endpoint, it will not generate code for that model. 
- If you want camel caps for a model name, property name, etc., you need to define things with a dash. E.g., storage-device will be StorageDevice, but storagedevice will just be Storagedevice
- TCG automatically appends Model, Schema, Controller, and Service to the name of your models that are defined in #/definitions. When naming your models, don't add "Model" to the end of the name otherwise it will display as StorageDeviceModelModel instead of just StorageDeviceModel.
- TCG only supports GET, PUT, POST, DELETE at the moment. There are plans to support PATCH.

#### Run TCG
```bash
python codegen.py path/to/openapi.json path/to/project/dir
```

#### After code generation
After code has been generated, you need to follow these steps to have a working api:
  
- Create services with correct names. Create a file services/your-package-name/services.py You can use this as an example to get something working (obviously, change "StorageDevice" to whatever  name of your resource is. It needs to match the resource name defined in models/controllers/schemas):

```python
import logging
import app

logger = logging.getLogger(app.config['DEFAULT_LOG_NAME'])


class StorageDeviceService():
    def put_before_validation(self, request_body):
        logger.info("PUT before validation for switch service")
        return request_body

    def put_after_validation(self, model):
        logger.info("PUT after validation for switch service")

    def post_before_validation(self, request_body):
        logger.info("POST before validation for switch service")
        return request_body

    def post_after_validation(self, model):
        logger.info("POST after validation for switch service")
```
- Create a database schema for each namespace tag name you have defined. E.g., if you have a path with a tag "x-faction-namespace=storage", create the database schema "storage" in your DB.
- Copy app/conf/app.conf to /etc/your-app-name/ and change the DB addresses. Dev is used by default when running the app, Test is used for unit tests. The others are not used by default for anything.
```bash
cd path/to/project/dir
python run.py
```
- Test the API using the REST client of your choice (I like Postman: https://www.getpostman.com/)

#### Future improvements/known issues
- Generate starter code so a brand new project can have something working immediately.
- Implement support for OAPI 3.0.
- Add support for links between resources instead of just foreign key ids.
- Separate file json schemas 
- Remove camel case dash thing
- Add support for overriding generated code 
    - Add meta tag in schema itself? Add param in cli? Annotation at file level?
- Only call service methods if they exist OR determine if method exists, and if not use base method.
- Add task resource to all methods with a collection of running tasks
- See if OAPI has ability to accept any additional attributes
- Decide best way to return tasks for sync/async completion (PATCH, POST?, DELETE)
- Only return tasks for async methods?
- Need a way to define if a method is sync/async, maybe in the json schema?
- Figure out many-to-many relationships in codegen
- Gitflow http://nvie.com/posts/a-successful-git-branching-model/
- Add support for query parameters
X change identifier to UUIDs instead of incremented integers

your-project-dir/
    resources/
        network/
            switch.json
            port.json
            interfaceList.json
        storage/
            storageDevice.json
    services/
        network/
            services.py
        storage/
            services.py
        
