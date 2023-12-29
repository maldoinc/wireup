While wireup tries to make it as easy as possible to test services by not modifying
the underlying classes in any way even when decorated, sometimes you need to be able
to swap a service object on the fly for a different one such as a mock.

This process can be useful in testing autowired targets for which there is no easy
way to pass a mock object.

The `container.override` property provides access to a number of useful methods
which will help temporarily overriding dependencies 
(See [override manager](class/override_manager.md)).


!!! info "Good to know"
    * Overriding only applies to subsequent autowire calls.
    * If a singleton service has been initialized, it is not possible to override any
    of its dependencies as the object is already in memory. You may need to override
    the first service directly instead of any transient dependencies.
    * When using interfaces override the interface rather than any impl.

## Example

```python
random_mock = MagicMock()
random_mock.get_random.return_value = 5

with self.container.override.service(target=RandomService, new=random_mock):
    # Assuming in the context of a web app:
    # /random endpoint has a dependency on RandomService
    # any requests to inject RandomService during the lifetime
    # of this context manager will result in random_mock being injected instead.
    response = client.get("/random")
```
