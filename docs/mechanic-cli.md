# mechanic CLI
### build
```bash
mechanic build <directory>
```
Generates code for you application based on the mechanic.yaml file located in <directory>. See 
[mechanic file reference](mechanicfile-reference.md) for more details.

### merge
```bash
mechanic merge <master> <files>...
```
Merges multiple OpenAPI 3.0 specifications into one. Useful in a microservices architecture, where you have many 
services and each one has it's own OpenAPI spec. The merge command will look for objects that have the 
'x-mechanic-public' extension, and merge them into the <master> file. Using this command allows you to decide which 
resources and APIs you want to expose in your documentation. 
