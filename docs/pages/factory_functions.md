Factory functions allow the container to wire dependencies that require additional logic to create 
or be able to inject objects it doesn't own.

Typically getting the necessary dependencies is enough to construct an object. However, there are scenarios
where you need to delegate the creation of an object to a special function called a 
[factory](https://en.wikipedia.org/wiki/Factory_(object-oriented_programming)){: target=_blank }.

## Use cases

Some of the use cases for factories are as follows:

* Object construction needs additional logic or configuration.
* Depending on the runtime environment or configuration, you may need to create different objects 
inheriting from the same base (See: [Strategy Pattern](https://en.wikipedia.org/wiki/Strategy_pattern){: target=_blank }) or configure them differently. 
* Gradually introduce DI into an existing project where the container should be able to inject dependencies created elsewhere. 
Such as injecting the same database connection as the rest of the application.
* Eliminate services which have only one method that returns the same object and instead inject the object directly.
    * Register the result of a service's method as its own service. Instead of calling `db_service.get_db()` every time,
      inject the session directly.

## Usage

In order for the container to inject these dependencies you must register the factory function.
You can do this by using the `@container.register` decorator or by calling `container.register(fn)` directly.

When the container needs to inject a dependency it checks known factories to see if any of them can create it.


!!! info
    The return type of the function tells the container what type of dependency it can create.

!!! warning
    Factories can only depend on objects known by the container!


## Links

* [Introduce to an existing project](introduce_to_an_existing_project.md)
