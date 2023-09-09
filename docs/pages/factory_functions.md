Factory functions allow the container to wire dependencies that require additional logic to create 
or be able to inject objects it doesn't own.

Typically getting the necessary dependencies is enough to construct an object. However, there are scenarios
where you need to delegate the creation of an object to a special function called a 
[factory](https://en.wikipedia.org/wiki/Factory_(object-oriented_programming)){: target=_blank }.

## Use cases

Some of the use cases for factories are as follows:

* Object construction needs additional logic or configuration.
* Depending on the runtime environment or configuration, you may need to create different objects 
inheriting from the same base (See [Strategy Pattern](https://en.wikipedia.org/wiki/Strategy_pattern){: target=_blank }) or configure them differently. 
* Gradually introduce DI into an existing project where the container should be able to inject dependencies created elsewhere. 
Such as injecting the same database connection as the rest of the application.
* Eliminate services which have only one method that returns the same object and instead inject the object directly.
    * A service that returns a db connection
    * A service which returns the current authenticated user
    * Register the result of a service's method as its own service. Instead of calling `auth_service.get_current_user()` every time, inject the authenticated user directly.

## Usage

In order for the container to inject these dependencies you must register the factory function.
You can do this by using the `@container.register` decorator or by calling `container.register(fn)` directly.

When the container needs to inject a dependency it checks known factories to see if any of them can create it.


!!! info 
    The return type of the function tells the container what type of dependency it can create.

!!! warning
    Factories can only depend on objects known by the container!

## Examples

Assume in the context of a web application a class `User` exists and represents a user of the system.

```python
# Instead of doing the following over and over again
def get_user_logs(auth_service: AuthService):
    current_user = auth_service.get_current_user()
    ...



# You can create a factory and inject the authenticated user directly.
# You may want to create a new type to make a disctinction on the type of user this is.
AuthenticatedUser = User

@container.register
def get_current_user(auth_service: AuthService) -> AuthenticatedUser:
    return auth_service.get_current_user()

# Now it is possible to inject the authenticated user directly wherever it is necessary.
def get_user_logs(user: AuthenticatedUser):
    ...
```

Assume a base class `Notifier` with implementations that define how the notification is sent (IMAP, POP, WebHooks, etc.)
Given a user it is possible to instantiate the correct type of notifier based on user preferences.


```python
@container.register
def get_user_notifier(user: AuthenticatedUser) -> Notifier:
    notifier_type = ...

    return container.get(notifier_type)
```

When injecting `Notifier` the correct type will be created based on the authenticated user's preferences.

## Links

* [Introduce to an existing project](introduce_to_an_existing_project.md)
