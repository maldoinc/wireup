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

## Injection

The container will perform autowiring based on the type hints given. No manual configuration is needed to inject
services.

To perform autowiring the method to be autowired must be decorated with `@container.autowire`. Given the nature of
Python decorators it is also possible to simply call it as a regular function which will return a callable with
arguments the containers knows about already bound.


## Lifetime

Services live in the container and their references are kept in it. As such, it should be avoided
that they contain data about any particular request as injected parameters are cached on their first autowire call.

The container should be configured once, at application startup and used throughout its execution.
Even though you can modify the container or parameters at runtime it is generally advised not to.
