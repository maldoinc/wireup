Wireup supports registering the same class multiple times under different qualifiers through the use of factories. 

A common use case for this would be to have multiple services connected to resources of the same underlying
type, such as maintaining multiple database connections: a main and a readonly copy.

## Example

Assume an application which has two databases set up: A main one and a readonly replica. In these scenarios the main
connection is used for writes while the readonly connection will be used to perform reads.

### Service registration via factories

```python title="db_service.py"
from typing import Annotated
from wireup import container, Wire

# Define a class that holds the base methods for interacting with the db.
class DatabaseService:
    def __init__(self, dsn: str) -> None:
        self.__connection = ...

    def query(self) -> ...:
        return self.__connection.query(...)


# Define a factory which creates and registers the service interacting with the main db.
# Register this directly without using a qualifier, this will be injected
# when services depend on DatabaseService.
@container.register
def main_db_connection_factory(
    dsn: Annotated[str, Wire(param="APP_DB_DSN")]
) -> DatabaseService:
    return DatabaseService(dsn)

# This factory registers the function using the qualifier "read"
# and requests the parameter that corresponds to the read replica DSN.
@container.register(qualifier="read")
def read_db_connection_factory(
    dsn: Annotated[str, Wire(param="APP_READ_DB_DSN")]
) -> DatabaseService:
    return DatabaseService(dsn)
```

### Usage

```python title="thing_repository.py"
from dataclasses import dataclass
from wireup import container

@container.register
@dataclass
class ThingRepository:
    # Main db connection can be injected directly as it is registered
    # without a qualifier, this makes it the "default" implementation.
    main_db_connection: DatabaseService
    
    # To inject the read connection the qualifier must be specified.
    read_db_connection: Annotated[DatabaseService, Wire(qualifier="read")]


    def create_thing(self, ...) -> None:
        return self.main_db_connection...

    def find_by_id(self, pk: int) -> Thing:
        return self.read_db_connection...
```




