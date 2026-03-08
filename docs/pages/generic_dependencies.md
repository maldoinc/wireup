Generic dependencies let you define reusable behavior
given a base class with a generic type parameter. This is useful when multiple dependencies share the same structure but work with different models, since you can keep the common logic in a generic base class and register concrete subclasses that bind the actual type.


## Sqlalchemy example

```python
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


@injectable
class BlogPostRepository(Repository[BlogPost]):
    model = BlogPost
```

You can now use `UserRepository` as usual.
