It can be challenging to add DI to an existing project which doesn't yet use it. One of the issues you will run into
sooner or later is being able to share resources between code which uses DI and the rest of the application 
which does not. 

This is especially useful to allow the container to inject dependencies created elsewhere.

Think of a database connection. Your application probably already has one. Instead of opening a second connection
using a new database service, you can instruct the container how to get the connection either via a service or
by using factory functions.

Another case might be an existing service that is already constructed, and you want to inject.

## Using a Service

A typical way to solve this would involve create a service with a single method 
that uses existing functionality to get the desired object and simply returns it.

```python
# Example of a service acting as a factory
@container.register
@dataclass
class DbConnectionService:
    self.conn = get_db_connection_from_somewhere()
```

Here, it is possible inject `DbConnectionService` and call `.conn` to get the connection. While this works, it's not the best way to go.

## Using Factory functions

To handle this more elegantly, Wireup lets you register functions as factories. 
You can do this by using the `@container.register` decorator or by calling `container.register(fn)` directly.


```python
@container.register
def get_db_connection_from_somewhere() -> Connection:
    return ...

# Alternatively

container.register(get_db_connection_from_somewhere)
```

Now it is possible to inject `Connection` just like any other dependency. 


## Links

* [Factory functions](factory_functions.md)
