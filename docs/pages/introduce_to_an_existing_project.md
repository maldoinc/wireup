For large existing projects, you may want to gradually add wireup to the project. One of the issues you will run into
sooner or later is being able to share resources between code that uses DI and the rest of the application 
which does not. 

This is especially useful to allow the container to inject dependencies created elsewhere.

Think of a database connection. Your application probably already has one. Instead of opening a second connection
using a new database service, instruct the container on how to get the connection by using factory functions.

Another case might be an existing service that is already constructed elsewhere, and you want to be able to inject it.

## Using Factory functions

In order to expose such resources to the container, use factory functions.

```python
@container.register
def db_connection_factory() -> Connection:
    return get_existing_db_configuration(...)
```

Now it is possible to inject `Connection` just like any other dependency. 


## Links

* [Factory functions](factory_functions.md)
