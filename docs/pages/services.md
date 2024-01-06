Use service objects to implement functionality in your application. Services can depend on configuration
or other services.

## Registration
Wireup does not enforce a structure, services may live anywhere in the application but must be registered 
with the container.

To register a class as a service the following options are available.

* Decorate the class using `container.register`.
* Call `container.register(YourService)` directly.
* Use `wireup.register_all_in_module`.
  (See: [Manual Configuration](manual_configuration.md#using-wireup-without-registration-decorators))

### Lifetime
By default, services will be registered as singletons. If your service or [Factory function](factory_functions.md)
needs to generate a fresh instance every time it is injected it needs to be registered with the `lifetime` parameter
set to `TRANSIENT`.

## Injection
Injection will be performed based on type hints. Most of the time no manual configuration 
is needed to inject services. 

!!! tip
    Refer to the documentation regarding [Annotations](annotations.md) for the exact details on when you need
    to explicitly annotate your dependencies.

### Autowiring
To perform autowiring the method to be autowired must be decorated with `@container.autowire`. Given the nature of
Python decorators it is also possible to call it as a regular function which will return a callable where
the container will perform dependency injection when called.


