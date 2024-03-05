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
* Inject a model/dto which represents the result of an action, such as the current authenticated user.

## Usage

In order for the container to inject these dependencies you must register the factory function.
You can do this by using the `@container.register` decorator or by calling `container.register(fn)` directly.

When the container needs to inject a dependency it checks known factories to see if any of them can create it.


!!! info
    * The return type of the function is mandatory to annotate as tells the container what 
    type of dependency it can create.
    * Factories can only depend on objects known by the container!

!!! warning
    Modules which perform service registration need to be imported otherwise any `@container.register` calls
    will not be triggered. This can be an issue when the service does not reside in the same file as the
    factory. 

    E.g: A model residing in `app.model.user` and the factory being in `app.service.factory`.
    If `app.service.factory` is never imported the container won't know how to build the user model.

    In those cases use `import_util.load_module` once on startup in order to trigger registrations.

## Examples

Assume in the context of a web application a class `User` exists and represents a user of the system.

```python
# Instead of doing the following over and over again
def get_user_logs(auth_service: AuthService):
    current_user = auth_service.get_current_user()
    ...



# You can create a factory and inject the authenticated user directly.
# You may want to create a new type to make a disctinction on the type of user this is.
AuthenticatedUser = NewType("AuthenticatedUser", User)

@container.register(lifetime=ServiceLifetime.TRANSIENT)
def get_current_user(auth_service: AuthService) -> AuthenticatedUser:
    return AuthenticatedUser(auth_service.get_current_user())

# Now it is possible to inject the authenticated user directly wherever it is necessary.
def get_user_logs(user: AuthenticatedUser):
    ...
```

Assume a base class `Notifier` with implementations that define how the notification is sent (IMAP, POP, WebHooks, etc.)
Given a user it is possible to instantiate the correct type of notifier based on user preferences.


```python
@container.register(lifetime=ServiceLifetime.TRANSIENT)
def get_user_notifier(user: AuthenticatedUser) -> Notifier:
    notifier_type = ...

    return container.get(notifier_type)
```

When injecting `Notifier` the correct type will be created based on the authenticated user's preferences.



## Links

* [Introduce to an existing project](introduce_to_an_existing_project.md)
