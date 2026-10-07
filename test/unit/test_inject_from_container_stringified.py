from __future__ import annotations

import pytest
import wireup
from wireup._decorators import inject_from_container


@wireup.injectable
class Bar: ...


@pytest.mark.parametrize("hide_annotated_names", [True, False])
def test_inject_from_container_contains_stringified_annotated_types(*, hide_annotated_names: bool) -> None:
    container = wireup.create_sync_container(injectables=[Bar])

    @inject_from_container(container, hide_annotated_names=hide_annotated_names)
    def get_bar(bar: wireup.Injected[Bar]) -> Bar:
        return bar

    assert get_bar() is container.get(Bar)
