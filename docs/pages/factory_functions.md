Typically getting the necessary dependencies is enough to construct an object. However, there are scenarios
where you need to delegate service creation to a special function called a 
[factory](https://en.wikipedia.org/wiki/Factory_(object-oriented_programming)){: target=_blank }.

## Use cases

* Object construction needs additional logic or configuration.
* Depending on the runtime environment or configuration, you may need to create different objects 
inheriting from the same base (See: [Strategy Pattern](https://en.wikipedia.org/wiki/Strategy_pattern){: target=_blank }) or configure them differently. 
* Inject a model/dto which represents the result of an action, such as the current authenticated user.
* Inject a class from another library where it's not possible to add annotations.

## Usage

In order for the container to inject these dependencies, you must register the factory function
by using the `@service` decorator or by calling `container.register(fn)` directly.

When the container needs to inject a dependency, it checks known factories to see if any of them can create it.


!!! info "Good to know"
    Return type annotation of the factory is required as it denotes what will be built.

## Examples

### Inject a model

Assume in the context of an application a class `User` exists and represents a user of the system.
We can use a factory to inject a user model that represents the current authenticated user.

```python
from wireup import service, ServiceLifetime

# You may want to create a new type to make a distinction on the type of user this is.
AuthenticatedUser = NewType("AuthenticatedUser", User)


@service(lifetime=ServiceLifetime.TRANSIENT)
def get_current_user(auth_service: AuthService) -> AuthenticatedUser:
    return AuthenticatedUser(auth_service.get_current_user())


# Now it is possible to inject the authenticated user directly wherever it is necessary.
@container.autowire
def get_user_logs(user: AuthenticatedUser):
    ...
```

### Implement strategy pattern

Assume a base class `Notifier` with implementations that define how the notification is sent (IMAP, POP, WebHooks, etc.)
Given a user it is possible to instantiate the correct type of notifier based on user preferences.


```python
from wireup import service, ServiceLifetime


@service(lifetime=ServiceLifetime.TRANSIENT)
def get_user_notifier(
    user: AuthenticatedUser, 
    slack_notifier: SlackNotifier, 
    email_mailer: EmailNotifier
) -> Notifier:
    notifier = ...  # get notifier type from preferences.

    return notifier
```

When injecting `Notifier` the correct type will be injected based on the authenticated user's preferences.

### Inject a third-party class

You can use factory functions to inject a class which you have not declared yourself and therefore cannot annotate. 
Let's take redis client as an example. 

=== "@ Annotations"

    ```python
    from wireup import service


    @service
    def redis_factory(redis_url: Annotated[str, Inject(param="redis_url")]) -> Redis:
        return redis.from_url(redis_url)
    ```

=== "🏭 Programmatic"

    ```python
    from wireup import service


    @service
    def redis_factory(settings: Settings) -> Redis:
        return redis.from_url(settings.redis_url)
    ```


## Links

* [Introduce to an existing project](introduce_to_an_existing_project.md)
