## Unit tests

Unit testing service objects is meant to be easy as the container does not interfere in
any way with the underlying classes.

Classes can be instantiated as usual in tests, and you need to pass dependencies 
such as services or parameters to them yourself.

To specify custom behavior for tests, provide a custom implementation 
or a subclass that returns test data as a dependency instead of mocks.

## Overriding

Sometimes you need to be able to swap a service object on the fly for a different one such as a mock.

The `container.override` property provides access to a number of useful methods and context managers
which help with overriding dependencies 
(See [override manager](class/override_manager.md)).


!!! info "Good to know"
    * Overriding only applies to future injections.
    * Once a singleton service has been instantiated, it is not possible to directly replace
    any of its direct or transitive dependencies via overriding as the object is already in memory.
    * When injecting interfaces and/or qualifiers, override the interface and/or qualifier 
    rather than the implementation that will be injected.


!!! tip
    If you're using an integration to get the container instance you can use the `wireup.integration.xxx.get_app_container` 
    method. This returns the container associated with your application.

### Examples

#### Context Manager
```python
random_mock = MagicMock()
# Chosen by fair dice roll. Guaranteed to be random.
random_mock.get_random.return_value = 4

with container.override.service(target=RandomService, new=random_mock):
    # Assuming in the context of a web app:
    # /random endpoint has a dependency on RandomService
    # requests to inject RandomService during the lifetime
    # of this context manager will result in random_mock being injected instead.
    response = client.get("/random")
```

#### Pytest

Similar to the above example but this uses pytest's autouse to achieve the same result.
Also shows how to use `get_app_container` when using integrations.

```python title="app.py"
def create_app():
    app = ...

    container = wireup.create_container(...)
    # Example shows FastAPI but any integration will work the same.
    wireup.integration.fastapi.setup(container, app)

    return app
```

```python title="conftest.py"
# This is a function scoped fixture which means 
# you'll get a fresh copy of the application and container every time.
@pytest.fixture
def app():
    return create_app()
```

```python title="some_test_file.py"
from wireup.integration.fastapi import get_app_container

def test_something_with_mocked_db_service(client: TestClient, app):
    with get_app_container(app).override.service(DBService, new=...):
        response = client.get("/some/path")

    # Assert response and mock calls.
```
