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

```python
from unittest.mock import MagicMock

random_mock = MagicMock()
random_mock.get_random.return_value = 4

with container.override.injectable(target=RandomService, new=random_mock):
    # Requests to inject RandomService during the lifetime
    # of this context manager will use random_mock instead.
    response = client.get("/random")
```

### Overriding Multiple Injectables

When you need to override several dependencies at once, use `container.override.injectables` with a list of
`InjectableOverride` objects:

```python
from unittest.mock import MagicMock
from wireup import InjectableOverride

user_service_mock = MagicMock()
order_service_mock = MagicMock()

overrides = [
    InjectableOverride(target=UserService, new=user_service_mock),
    InjectableOverride(target=OrderService, new=order_service_mock),
]

with container.override.injectables(overrides=overrides):
    # Both UserService and OrderService are now mocked
    response = client.get("/checkout")
```

### Nested Overrides

`container.override` supports nested overrides for the same target. The innermost override is active, and exiting
restores the previous value. There are 2 ways to utilise nested overrides:

#### Context Managers

```python
@injectable
class Foo:
    pass


container = wireup.create_sync_container(injectables=[Foo])

outer = MagicMock(spec=Foo)
inner = MagicMock(spec=Foo)

with container.override.injectable(Foo, new=outer):
    assert container.get(Foo) is outer

    with container.override.injectable(Foo, new=inner):
        assert container.get(Foo) is inner

    assert container.get(Foo) is outer
assert type(container.get(Foo)) is Foo
```

#### Manual `set` and `delete`

```python
@injectable
class Foo:
    pass


container = wireup.create_sync_container(injectables=[Foo])

mock1 = MagicMock(spec=Foo)
mock2 = MagicMock(spec=Foo)

container.override.set(Foo, new=mock1)
container.override.set(Foo, new=mock2)

assert container.get(Foo) is mock2

container.override.delete(Foo)

assert container.get(Foo) is mock1

container.override.delete(Foo)

assert type(container.get(Foo)) is Foo
```

A real-world example where this could be useful is if your application depends on a full-fledged database. However, in
tests you want to override that dependency to use an in-memory database, and in one of the tests you want to override
the dependency again to test an error case where the database throws a foreign key exception.

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
@pytest.fixture
def in_memory_db():
    return InMemoryDBService()

# This is a function scoped fixture which means
# you'll get a fresh copy of the application and container every time.
@pytest.fixture
def app(in_memory_db):
    with get_app_container(app).override.injectable(DBService, new=in_memory_db):
        return create_app()
```

```python title="some_test_file.py"
from wireup.integration.fastapi import get_app_container


def test_db_foreign_key_exception(client: TestClient, app):
    mock_db = MagicMock()
    # mock db to throw exception
    with get_app_container(app).override.injectable(DBService, new=mock_db):
        response = client.get("/some/path")

        # Assert response and mock calls.
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
    with get_app_container(app).override.injectable(DBService, new=...):
        response = client.get("/some/path")

    # Assert response and mock calls.
```

## Next Steps

- [Container](container.md) - Learn about the container API.
- [Lifetimes & Scopes](lifetimes_and_scopes.md) - Understand how lifetimes affect testing.
