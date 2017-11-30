# mechanicfile reference

##### APP_NAME
**Required**: No  
**Default value**: "app"  
Option to name your application, this value is used for defining the package name to contain app init file.

##### OPENAPI
**Required**: Yes  
**Default value**: None  
Path to the OpenAPI 3.0 file to generate from. Example "v100.yaml" or "~/v100.yaml". Relative to the location of the
config file.

##### MODELS_PATH 
**Required**: No  
**Default value**: models/{{namespace}}.py   
Defines the path in which to generate SQLAlchemy models. Optional variables are:
- {{namespace}} --> The namespace associated with the model. See [namespaces](#namespaces) for more details.  
- {{version}} --> The OpenAPI 3.0 version defined in the "info" section. Characters not appropriate for python packages 
will be removed, such as dots and dashes. For example, if {{version}} == "1.0.0", the folder name will be "100".

##### SCHEMAS_PATH 
**Required**: No  
**Default value**: schemas/{{namespace}}.py   
Defines the path in which to generate Marshmallow schemas. Optional variables are:
- {{namespace}} --> The namespace associated with the schema. See [namespaces](#namespaces) for more details.   
- {{version}} --> The OpenAPI 3.0 version defined in the "info" section. Characters not appropriate for python packages 
will be removed, such as dots and dashes. For example, if {{version}} == "1.0.0", the folder name will be "100".

##### CONTROLLERS_PATH 
**Required**: No  
**Default value**: controllers/{{namespace}}.py   
Defines the path in which to generate controllers. Optional variables are:
- {{namespace}} --> The namespace associated with the schema. See [namespaces](#namespaces) for more details.   
- {{version}} --> The OpenAPI 3.0 version defined in the "info" section. Characters not appropriate for python packages 
will be removed, such as dots and dashes. For example, if {{version}} == "1.0.0", the folder name will be "100".

##### MODELS_NAME_PATTERN
**Required**: No  
**Default value**: {{resource}}Model  
Defines how model classes should be named. Optional variables are:
- {{resource}} --> The resource defined in the OpenAPI 3.0 file.
- {{namespace}} --> The namespace associated with the schema. See [namespaces](#namespaces) for more details.   
- {{version}} --> The OpenAPI 3.0 version defined in the "info" section (without dots or dashes)

##### SCHEMAS_NAME_PATTERN
**Required**: No  
**Default value**: {{resource}}Schema  
Defines how schema classes should be named. Optional variables are:
- {{resource}} --> The resource defined in the OpenAPI 3.0 file.
- {{namespace}} --> The namespace associated with the schema. See [namespaces](#namespaces) for more details.   
- {{version}} --> The OpenAPI 3.0 version defined in the "info" section (without dots or dashes)

##### CONTROLLERS_NAME_PATTERN
**Required**: No  
**Default value**: {{resource}}{{controller_type}}Controller  
Defines how controller classes should be named. Optional variables are:
- {{resource}} --> The resource defined in the OpenAPI 3.0 file.
- {{namespace}} --> The namespace associated with the schema. See [namespaces](#namespaces) for more details.   
- {{version}} --> The OpenAPI 3.0 version defined in the "info" section (without dots or dashes)
- {{controller_type}} --> For more details about different controller types, see [controllers](#controllers).

##### BASE_API_PATH
**Required**: No  
**Default value**: /api  
Allows you to define the base api path for your REST API.

##### DEFAULT_NAMESPACE
**Required**: No  
**Default value**: "default"  
Allows you to define the default namespace if the "x-mechanic-namespace" extension is not used. For more details about
extensions, see [here](#extensions) for more details.

##### EXCLUDE
**Required**: No  
**Default value**: []
Allows you to customize which files to exclude in the code generation. This is useful if, for example, you decided to 
manually change code in a file and you don't want it to be overwritten. The path is relative to root dir of the project.
```yaml
EXCLUDE: ["run.py", "myappname/__init__.py", "schemas/v100/abc.py"] 
```
 
##### OVERRIDE_BASE_CONTROLLER
**Required**: No  
**Default value**: None  
Allows finer grained control over which controllers inherit from which class. For example, let's say you've defined 
BASE_CONTROLLER as "controllers.base.MyCustomBaseController", but you want only a specific file to inherit instead from 
"controllers.base.MySpecificBaseController". You would use this attribute to define that. Here are some examples:  

This means that "HouseController" will have "MyCustomBaseController" as it's super class, 
instead of the value defined by BASE_CONTROLLER
```yaml
OVERRIDE_BASE_CONTROLLER: 
    - with: "controllers.base.MyCustomBaseController",
      for: ["controllers.default.HouseController"]
    - with: "controllers.base.MyCustomBaseController2",
      for: ["controllers.default.ParkController"]
```

This example means that all Controllers will inherit from "MyCustomBaseController".
```yaml
OVERRIDE_BASE_CONTROLLER:
    - with: "controllers.base.MyCustomBaseController",
      for: "all"
```

This example means that all Controllers except "HouseController" and "ParkController" will inherit from "MyCustomBaseController".
```yaml
OVERRIDE_BASE_CONTROLLER:
    - with: "controllers.base.MyCustomBaseController",
      for: "all",
      except: ["controllers.default.HouseController", "controllers.default.ParkController"]
```

##### OVERRIDE_BASE_MODEL
**Required**: No  
**Default value**: None  
Same as [OVERRIDE_BASE_CONTROLLER](#override-base-controller) except for models

##### OVERRIDE_BASE_SCHEMA
**Required**: No  
**Default value**: None  
Same as [OVERRIDE_BASE_CONTROLLER](#override-base-controller) except for schemas

##### OVERRIDE_CONTROLLER_TYPE
**Required**: No  
**Default value**: None  
```yaml
OVERRIDE_CONTROLLER_TYPE:
  "/uri/as/defined/in/oapi/spec": "Collection"
  "/myseconduri/as/defined/in/oapi/spec": "Item"
```

##### OVERRIDE_TABLE_NAMES
**Required**: No  
**Default value**: None  
Allows you to override the generated table name for a model.
```yaml
OVERRIDE_TABLE_NAMES:
  - with: "mytablename",
    for: "models.abc.MyModel"
  - with: "anothertablename",
    for: "models.abc.House"
```

##### OVERRIDE_DB_SCHEMA_NAMES
**Required**: No  
**Default value**: None  
Same as [OVERRIDE_TABLE_NAMES](#override-table-names) except for db schema names.

##### DEFAULT_BASE_MODEL
**Required**: No  
**Default value**: mechanic.base.models.MechanicBaseModelMixin  
Specify your own base model mixin for sqlalchemy, instead of the default mechanic.base.models.MechanicBaseModelMixin.

##### DEFAULT_BASE_SCHEMA
**Required**: No  
**Default value**: mechanic.base.schemas.MechanicBaseSchema  
Specify your own base marshmallow schema instead of the default mechanic.base.schemas.MechanicBaseSchema.

##### DEFAULT_BASE_MODEL_SCHEMA
**Required**: No  
**Default value**: mechanic.base.schemas.MechanicBaseModelSchema  
Specify your own base marshmallow schema instead of the default mechanic.base.schemas.MechanicBaseModelSchema.

##### DEFAULT_BASE_CONTROLLER
**Required**: No  
**Default value**: mechanic.base.controllers.MechanicBaseController  
Specify your own base controller instead of the default mechanic.base.controllers.MechanicBaseController.

##### DEFAULT_BASE_ITEM_CONTROLLER
**Required**: No  
**Default value**: mechanic.base.controllers.MechanicBaseItemController  
Specify your own base item controller instead of the default mechanic.base.controllers.MechanicBaseItemController.

##### DEFAULT_BASE_COLLECTION_CONTROLLER
**Required**: No  
**Default value**: mechanic.base.controllers.MechanicBaseCollectionController  
Specify your own base collection controller instead of the default mechanic.base.controllers.MechanicBaseCollectionController.

##### EXCLUDE_MODEL_GENERATION
**Required**: No  
**Default value**: []  
A list of resources that should NOT be generated as models. Use the schema name associated with the object in the OpenAPI 3.0 file. 
```yaml
EXCLUDE_MODEL_GENERATION: ["Pet", "DogToy"]
```
To not generate any models:
```yaml
EXCLUDE_MODEL_GENERATION: "all"
```
##### EXCLUDE_SCHEMA_GENERATION
**Required**: No  
**Default value**: []  
Same as [EXCLUDE_MODEL_GENERATION](#exclude-model-generation) except for schemas.

##### EXCLUDE_CONTROLLER_GENERATION
**Required**: No  
**Default value**: []  
Same as [EXCLUDE_MODEL_GENERATION](#exclude-model-generation) except for controllers.

##### OVERRIDE_CONTROLLER_FOR_URI
**Required**: No  
**Default value**: None
Specify your own custom controllers to replace with the generated ones. Let's say you want to customize the behavior of 
a controller for a specific resource (or entirely replace it). You can tell mechanic to point to your specified controller 
instead of the generated one. Use the uri (exactly as defined in the OpenAPI spec) as the key, and the value as the
module path to your controller.
 
 ```yaml
OVERRIDE_CONTROLLER_FOR_URI:
  "/groceries/apples": "mypackage.controllers.MyAppleController",
  "/groceries/apples/{id}": "mypackage.controllers.MyAppleItemController"
 ```
 
##### DATABASE_URL
**Required**: Yes  
**Default value**: None
Should be of the format <db-type>://<username>:<password>@<hostname>:<port>/<db_name>