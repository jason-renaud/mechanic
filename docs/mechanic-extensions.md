# mechanic OpenAPI extensions 
| extension                 | description |
| ---------                 | ----------- |
| x-mechanic-namespace      | A way to separate categories of APIs/schemas. This is used to determine which packages to separate code into. If not defined, mechanic will default to defining the object's namespace as 'default'. |
| x-mechanic-public         | Allows you to mark an API and an object as 'public'. If not using the mechanic-merge tool, this will most likely be irrelevant to you. Otherwise, see [mechanic-merge](mechanic-cli.md#merge) for more details. |
| x-mechanic-embeddable     | Set to 'true' if this attribute can either be represented as a uri or as a nested object. If set to true, it is required that the attribute is defined as 'oneOf', with one item being a $ref to a schema, and the other item being a 'string'. |

### x-mechanic-embeddable
Let's say you have a schema, House, defined as such:
```yaml
House:
    type: object
    properties:
      bedrooms:
        type: integer
      bathrooms:
        type: integer
```
And then in person.yaml, you have:
```yaml
Person:
    type: object
    properties:
      name:
        type: string
      house:
        $ref: house.yaml#House
```

Assuming you've set up your API paths in the OpenAPI file, doing a GET on a Person will return something like this:
```json
{
  "identifier": "...",
  "uri": "...",
  "name": "Taylor Swift",
  "house": {
    "identifier": "123-456-789-458",
    "uri": "/api/houses/123-456-789-458",
    "bedrooms": 2,
    "bathrooms": 2
  }
}
```
For a simple example like this, having the object embedded is not a big deal. But if you have an object that has 10 or 
20 nested objects, it could get annoying. mechanic allows you to define a nested object as 'embeddable', meaning that it
be represented as a uri instead of the entire object. In the example above, you would change your Person object to be
this:

```yaml
Person:
    type: object
    properties:
      name:
        type: string
      house:
        x-mechanic-embeddable: true
        oneOf:
          - $ref: house.yaml#House
          - type: string
```

Then doing a GET on that Person again will return this instead:
```json
{
  "identifier": "...",
  "uri": "...",
  "name": "Taylor Swift",
  "house": "/api/houses/123-456-789-458"
}
```
And if you use the "embed" query parameter, it will return the nested object instead. E.g. GET 
http://myapi.com/api/people/{id}?embed=house.  
**Important:** marking an attribute as 'embeddable' means that oneOf MUST contain both a $ref and a string.