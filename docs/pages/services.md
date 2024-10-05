Use service objects to implement functionality in your application. Services can depend on configuration or other services.

## Registration
Wireup does not enforce a code structure. Services may live anywhere, but must be registered with the container. 

To register a class as a service you can decorate it with `@service` or `@abstract`.

### Lifetime
By default, the container will keep in memory only a single copy of each service. 
If you need to generate fresh instances every time a service is injected, 
then it needs to be registered with the `lifetime` parameter set to `TRANSIENT`.

## Injection
Injection will be performed based on type hints. Most of the time no manual configuration is needed.

!!! tip
    Refer to the documentation regarding [Annotations](annotations.md) for the exact details on when you need
    to explicitly annotate your dependencies.
