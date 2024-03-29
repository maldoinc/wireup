## Unit tests

Unit testing service objects is meant to be easy as the container does not interfere in
any way with the underlying classes.

Classes can be instantiated as usual in tests, and you need to pass dependencies 
such as services or parameters to them yourself.

To specify custom behavior for tests, provide a custom implementation 
or a subclass that returns test data as a dependency instead of mocks.

It is also possible to use the container to build a part of your dependencies by
calling `container.get(ThingService)` which will return a `ThingService` instance.

## Overriding

While wireup tries to make it as easy as possible to test services by not modifying
the underlying classes in any way even when decorated, sometimes you need to be able
to swap a service object on the fly for a different one such as a mock.

This process can be useful in testing autowired targets such as an api endpoint 
for which there is no easy way to pass a mock object as it's not being called directly
by the test.

The `container.override` property provides access to a number of useful methods
which will help temporarily overriding dependencies 
(See [override manager](class/override_manager.md)).


!!! info "Good to know"
    * Overriding only applies to future autowire calls.
    * It is possible to override services directly.
    * Once a singleton service has been instantiated, it is not possible to directly replace
    any of its direct or transitive dependencies via overriding as the object is already in memory.
        * You will need to call `container.clear_initialized_objects()` and then override the 
        desired service. This will make the container use the override when the 
        new copy of the service is being built.
    * When using interfaces and/or qualifiers, override the interface and/or qualifier rather than the implementation 
    that will be injected.

### Examples

#### Context Manager
```python
random_mock = MagicMock()
# Chosen by fair dice roll. Guaranteed to be random.
random_mock.get_random.return_value = 4

with self.container.override.service(target=RandomService, new=random_mock):
    # Assuming in the context of a web app:
    # /random endpoint has a dependency on RandomService
    # requests to inject RandomService during the lifetime
    # of this context manager will result in random_mock being injected instead.
    response = client.get("/random")
```

#### Python unittest

Use the setup method to replace a service with a mock for the duration of the test. 

```python
class SomeEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_service = MagicMock()
        
        # Drop references to initialized objects.
        # Services or autowire targets requesting DBService
        # will get the mocked object instead.
        container.clear_initialized_objects()
        container.override.service(DbService, new=self.db_service)
```

#### Pytest

Similar to the above example but this uses pytest's autouse to achieve the same result.

```python
@pytest.fixture(autouse=True)
def setup_container(db_service_mock: MagicMock) -> None:
    container.clear_initialized_objects()
    container.override.service(DbService, new=db_service_mock)

def test_something_with_mocked_db_service(client: TestClient, db_service_mock: MagicMock):
    # Set up the db service mock
    db_service_mock.get_things.return_value = ...
    response = client.get("/some/path")

    # Assert response and mock calls.
```
