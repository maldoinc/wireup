Wireup has support for string types or `from __future__ import annotations`. 
To enable this, you must install the `eval_type_backport` package, also used in Pydantic and FastAPI among others.

!!! tip "Good to know"
    * Services/factories must be defined at the module level. Registering types declared inside functions is not supported.
    * Types used by Wireup MUST NOT be moved into `TYPE_CHECKING` blocks. Doing so, makes them unavailable at runtime for inspection.




Take the following code for example. Ruff/flake8 will suggest to move the `Iterator` and `Thing` imports into a type checking block, but doing so
prevents the import from happening during runtime and as such Wireup will not be able to resolve the type.

You should pay extra attention to this if you use the `TCH` rules from Ruff.

```python
from collections.abc import Iterator

@service
def thing_factory() -> Iterator[Thing]:
    yield Thing()


@service
@dataclass
class ExampleService:
    thing: Thing

```