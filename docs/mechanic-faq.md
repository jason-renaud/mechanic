# FAQ
### What if my OpenAPI file is split across many files?
mechanic automatically merges your OpenAPI file if it is split in a particular way. External references must be relative
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

### What version of Python do I need?
Python 3.6+.

### What is a 'collection' controller and what is an 'item' controller?
mechanic has 2 types of controllers - Collection, and Item. If the endpoint uri does not match one of these patterns (#1 and #2 below), 
there will be no base implementation for the controller. A collection controller represents a collection of resources. 
An API with no parameters in the endpoint definition will be defined as a 'Collection' controller. An item controller 
represents a single resource, and has exactly one parameter in the endpoint, and it is at the end of the uri.

For example, let's say you have 4 endpoints defined like this:

1) /cars/wheels
2) /cars/wheels/{id}
3) /cars/wheels/{id}/rotate/{direction}
4) /cars/wheels/{id}/replace

\#1 will be mapped as an Item controller, \#2 will be mapped as a Collection controller, \#3 and \#4 do not match an Item
or Collection pattern, so they will be named WheelRotatedirectionController and WheelReplaceController. Because these
controllers are non-Item and non-Collection, you will likely want to override them for it to be useful. See
[here](mechanicfile-reference.md#override_controller_for_uri) for more details.  

A collection controller will inherit from 
[DEFAULT_BASE_COLLECTION_CONTROLLER](mechanicfile-reference.md#default_base_collection_controller). An item controller 
will inherit from [DEFAULT_BASE_ITEM_CONTROLLER](mechanicfile-reference.md#default_base_item_controller). Other 
controllers will inherit from [DEFAULT_BASE_CONTROLLER](mechanicfile-reference.md#default_base_controller).