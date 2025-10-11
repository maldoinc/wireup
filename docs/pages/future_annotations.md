# Type Annotations Support

Wireup supports string type annotations and `from __future__ import annotations` when the `eval_type_backport` package is installed.

## Important Requirements

1. Define services and factories at the module level only. Inner function definitions are not supported.
2. Keep type imports accessible at runtime - don't move them to `TYPE_CHECKING` blocks.

## Example

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator  # Don't do this!


@service
def thing_factory() -> Iterator[Thing]:  # This needs the import at runtime
    yield Thing()

@service
class Service:
    def __init__(self, thing: Thing): # This too needs the import at runtime
        pass
```

!!! warning
    If you use Ruff/flake8 with rules like `TCH`, be careful not to move required imports into `TYPE_CHECKING` blocks.