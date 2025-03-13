# Multiple Service Registrations

Use factories to register multiple instances of the same class with different qualifiers. This is useful for scenarios where you need multiple configurations of the same service type.

## Example: Multi-Database Setup

Here's how to set up multiple database connections - a common scenario where you have a primary database for writes and a replica for reads.

### Registration

```python title="db_service.py"
from typing import Annotated
from wireup import service, Inject

class DatabaseService:
    def __init__(self, dsn: str) -> None:
        self.__connection = ...  # Connection initialization

    def query(self) -> ...:
        return self.__connection.query(...)

@service  # Default connection for writes
def primary_db(
    dsn: Annotated[str, Inject(param="PRIMARY_DB_DSN")]
) -> DatabaseService:
    return DatabaseService(dsn)

@service(qualifier="replica")  # Read-only connection
def replica_db(
    dsn: Annotated[str, Inject(param="REPLICA_DB_DSN")]
) -> DatabaseService:
    return DatabaseService(dsn)
```

### Usage

```python title="repository.py"
@service
@dataclass
class Repository:
    primary: DatabaseService  # Default connection
    replica: Annotated[DatabaseService, Inject(qualifier="replica")]

    def save(self, data: dict) -> None:
        return self.primary.query(...)  # Write operations

    def get(self, id: int) -> dict:
        return self.replica.query(...)  # Read operations
```

The container will inject the appropriate database connection based on whether a qualifier is specified.