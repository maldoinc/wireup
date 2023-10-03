Services are classes known by the container that provide functionality.

Contrary to static utility classes or methods they usually rely on other services or [parameters](parameters.md) to
provide a part of their functionality.

Examples refer to the default container provided by the library in `wireup.container` but any other instance can be
used in its place. The process is meant to be simple and the short [Quickstart](quickstart.md) page shows by example and
already contains all the key concepts you need to know about.

## Registration
Declaration and usage of services is designed to be as simple as possible. They may live anywhere in the application
but must be registered with the container.

To register a class as a service the following options are available.

* Decorate the class using the `container.register`.
* Call `container.register(YourService)` directly on the service.
* Use `container.register_all_in_module`.
  (See: [Manual Configuration](manual_configuration.md#using-wireup-without-registration-decorators))

### Singleton or Transient
Services, by default will be registered as singletons. If your service or [Factory function](factory_functions.md)
needs to generate a fresh instance every time it is injected it needs to be registered with the `lifetime` parameter
set to `TRANSIENT`.

!!! tip
    Use `container.register(lifetime=ServiceLifetime.TRANSIENT)` when the service relies on state that may change during execution.
    Such as an `AuthService` which relies on data from the current request in the context of a web application.

## Injection
The container will perform autowiring based on the type hints given. No manual configuration is needed to inject
services.

### Autowiring
To perform autowiring the method to be autowired must be decorated with `@container.autowire`. Given the nature of
Python decorators it is also possible to simply call it as a regular function which will return a callable with
arguments the containers knows about already bound.

### Explicit injection annotation
By default, the container will ignore any types it doesn't know about when autowiring. If you want to be explicit
about what dependencies are to be injected and have it raise if they are unknown, you can annotate the type.

```python
@container.autowire
def target(random_service: Annotated[RandomService, Wire()]):
    ...
```

## Lifetime

Services live in the container and their references are kept in it. By default, services will be instantiated
only once and all subsequent requests to them will return the same instance.

To override this behavior you must register the service or factory function with by setting the `lifetime` parameter
to `TRANSIENT` when registering as service

```python
container.register(lifetime=ServiceLifetime.TRANSIENT)
```

The container should be configured once, at application startup and used throughout its execution.
Even though you can modify the container or parameters at runtime it is generally advised not to.
