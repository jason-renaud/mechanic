# Customizing behavior
### Overriding default base controllers
So you've generated code from your API spec file, and everything is working. But now you want to add some additional 
functionality to your app. You want to implement sort, limit, and filter query parameters for all of your resources. In 
order to do this, you will need to override the mechanic default base controllers, using one or more of the following 
mechanic file options:
- DEFAULT_BASE_CONTROLLER
- DEFAULT_BASE_ITEM_CONTROLLER
- DEFAULT_BASE_COLLECTION_CONTROLLER

In this particular example, you will probably want to use just 
[DEFAULT_BASE_COLLECTION_CONTROLLER](mechanicfile-reference.md#default_base_collection_controller). First edit your 
mechanic.yaml file and add this:
```yaml
DEFAULT_BASE_COLLECTION_CONTROLLER: "module.path.to.my.CustomCollectionController"
```
Then add your custom code to handle things however you like. All "collection" controllers will now inherit from 
CustomCollectionController, instead of MechanicBaseCollectionController. If you want to take advantage of the existing 
base controller, simply have CustomCollectionController inherit from MechanicBaseCollectionController, and you can just 
override the methods you need.

### Overriding default base schemas
There are 2 types of Marshmallow schemas in mechanic: ModelSchema and Schema. ModelSchema is exactly what it sounds 
like, a schema representation of a model. You can see marshmallow-sqlalchemy documentation for more details. A Schema 
is a Marshmallow schema that is not dependent on a model. Maybe you have an API where the request body is a set of 
parameters to execute a command, and you are not interested in saving it to the database.  

You will want to use [DEFAULT_BASE_SCHEMA](mechanicfile-reference.md#default_base_schema) or 
[DEFAULT_BASE_MODEL_SCHEMA](mechanicfile-reference.md#default_base_model_schema) to customize the base schemas for your 
app. This is conceptually the same as customizing base controllers.

### Overriding the default base model
SQLAlchemy allows you to use a "mixin" instead of a base class. This is the same as adding a custom base controller or 
a custom base schema, except for models instead. See [DEFAULT_BASE_MODEL](mechanicfile-reference.md#default_base_model)

### Overriding the base controller for a specific controller
Let's say you only want to override the base controller for 1 or 2 controllers, instead of all of them. You can use 
[OVERRIDE_BASE_CONTROLLER](mechanicfile-reference.md#override_base_controller).   

### Overriding the base schema for a specific schema
See [OVERRIDE_BASE_SCHEMA](mechanicfile-reference.md#override_base_schema)

### Overriding the base model for a specific model
See [OVERRIDE_BASE_MODEL](mechanicfile-reference.md#override_base_model)

### Using a custom controller instead of the generated one
See [OVERRIDE_CONTROLLER_FOR_URI](mechanicfile-reference.md#override_controller_for_uri). Using this will route the 
particular endpoint to your controller instead of the generated one.

