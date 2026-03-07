Use standard Python generics by putting the shared behavior in a generic base class, then registering concrete subclasses that bind the concrete type.

## Sqlalchemy example

```python hl_lines="17-20"
from sqlalchemy import select
from sqlalchemy.orm import Session

from wireup import injectable


class Repository[T]:
    model: type[T]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, id: int) -> T | None:
        return self.session.get(self.model, id)


@injectable
class UserRepository(Repository[User]):
    model = User
```

You can now use `UserRepository` as usual.
