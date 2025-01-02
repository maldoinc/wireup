Use service objects to implement functionality in your application. Services can depend on configuration or other services.

## Registration
Wireup does not enforce a code structure. Services may live anywhere, but must be registered with the container. 

To register a class as a service you can decorate it with `@service` or `@abstract`. In addition, the modules
where services reside must be passed to the `service_modules` parameter in the `wireup.create_container` call.

!!! tip "Good to know"
    Note that you don't need to register each module separately, only the top level modules are sufficient
    as the container will perform a recursive scan.


### Lifetime
By default, the container will keep in memory only a single copy of each service. 
If you need to generate fresh instances every time a service is injected, 
then it needs to be registered with the `lifetime` parameter set to `TRANSIENT`.

## Injection
To request a service in another serivce simply set the type in the init method.
The name of the argument does not matter, only the type is used to detect dependencies.


```python
@service
class FooService:
    def __init__(self, bar: BarService) -> None: ...
```

Most of the time no additional configuration is needed.

!!! tip
    Refer to the documentation regarding [Annotations](annotations.md) for the exact details on when you need
    to explicitly annotate your dependencies.
