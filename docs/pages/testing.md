The `@injectable` decorator doesn't modify your classes, so they can be instantiated and tested like any regular Python
class. Pass dependencies manually in your tests.

```python
from unittest.mock import MagicMock


def test_user_service_logic():
    # Arrange: Create dependencies manually (mocks or real)
    repo_mock = MagicMock()
    repo_mock.get.return_value = User(id=1, name="Test User")

    # Act: Instantiate the service with the mock
    service = UserService(repository=repo_mock)
    result = service.get_user_name(1)

    # Assert: Verify behavior
    assert result == "Test User"
    repo_mock.get.assert_called_once_with(1)
```

To specify custom behavior for tests, provide a custom implementation or a subclass that returns test data.

## Overriding

Sometimes you need to be able to swap a dependency on the fly for a different one such as a mock.

The `container.override` property provides access to a number of useful methods and context managers which help with
overriding dependencies (See [override manager](class/override_manager.md)).

!!! info "Good to know"

    - Overriding only applies to future injections.
    - Once a singleton has been instantiated, it is not possible to directly replace any of its direct or transitive
        dependencies via overriding as the object is already in memory.
    - When injecting interfaces and/or qualifiers, override the interface and/or qualifier rather than the implementation
        that will be injected.

!!! tip

    If you're using an integration to get the container instance you can use the `wireup.integration.xxx.get_app_container`
    method. This returns the container associated with your application.

### Context Manager

The `container.override` context manager allows you to replace one or more dependencies for the duration of a the
context manager. It supports overriding both standard injectables and those with qualifiers.

```python
from unittest.mock import MagicMock

random_mock = MagicMock()
random_mock.get_random.return_value = 4

user_service_mock = MagicMock()

with container.override(
    {
        RandomService: random_mock,
        UserService: user_service_mock,
        (Database, "read_replica"): MagicMock(),
    }
):
    # Requests to inject the overriden dependencies during the lifetime
    # of this context manager will result in the replaced objects instead.
    response = client.get("/random")
```

### Permanent Overrides

You can also set permanent overrides using `container.override.set()`. These will persist until manually cleared. This
is useful when you want to set global overrides for a suite of tests or when using a test runner that tears down the
container for you.

```python
from unittest.mock import MagicMock

# Set a permanent override
container.override.set(target=UserService, new=MagicMock())

# Clear a specific override
container.override.delete(target=UserService)

# Clear all overrides
container.override.clear()
```

### Pytest

```python title="app.py"
import wireup


def create_app():
    app = ...

    container = wireup.create_async_container(...)
    # Example shows FastAPI but any integration works the same.
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
    with get_app_container(app).override({DBService: MagicMock()}):
        response = client.get("/some/path")

    # Assert response and mock calls.
```

## Next Steps

- [Container](container.md) - Learn about the container API.
- [Lifetimes & Scopes](lifetimes_and_scopes.md) - Understand how lifetimes affect testing.
