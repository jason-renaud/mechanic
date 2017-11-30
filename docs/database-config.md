#### Database configuration
This assumes you already have a sql database created.   

If you use the [x-mechanic-namespace](mechanic-extensions.md) extension, create
a schema named the same as each usage [x-mechanic-namespace](mechanic-extensions.md).
For example, let's say in your spec you have something like this:
```yaml
paths:
    /airplanes:
      x-mechanic-namespace: sky
      get: ...
      post: ...
    /cars: 
      get: ...
      post: ...
    /boats:
      x-mechanic-namespace: water
      get: ...
      post: ...
```
In this scenario, you need to define schemas "sky", "water", and "default". "default" is the schema name used when no
[x-mechanic-namespace](mechanic-extensions.md) definition is used to define either
an operation or a OpenAPI schema object.  

If you do not define these schemas in your database, you will see a database error when attempting to run your application.