import re
from dataclasses import dataclass

import pytest
import wireup
from typing_extensions import Annotated
from wireup.errors import WireupError

from test.unit.services.no_annotations.random.random_service import RandomService


def test_dependencies_parameters_exist() -> None:
    @wireup.service
    def foo_service(_param: Annotated[str, wireup.Inject(param="foo")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=(
            "Parameter '_param' of Type test.unit.services.no_annotations.random.random_service.RandomService "
            "depends on an unknown Wireup parameter 'foo'."
        ),
    ):
        wireup.create_sync_container(services=[foo_service])


def test_parameters_exist_checks_expression() -> None:
    @wireup.service
    def foo_service(_param: Annotated[str, wireup.Inject(expr="${foo}-${foo}")]) -> RandomService:
        return RandomService()

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter '_param' of Type test.unit.services.no_annotations.random.random_service.RandomService "
            "depends on an unknown Wireup parameter 'foo' requested in expression '${foo}-${foo}'."
        ),
    ):
        wireup.create_sync_container(services=[foo_service])


def test_checks_dependencies_exist() -> None:
    class Foo: ...

    @wireup.service
    @dataclass
    class Bar:
        foo: Foo

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'foo' of Type test.unit.test_container_creation.Bar "
            "depends on an unknown service Type test.unit.test_container_creation.Foo with qualifier None."
        ),
    ):
        wireup.create_sync_container(services=[Bar])


def test_lifetimes_match() -> None:
    @wireup.service(lifetime="scoped")
    class ScopedService: ...

    @wireup.service
    @dataclass
    class SingletonService:
        scoped: ScopedService

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'scoped' of Type test.unit.test_container_creation.SingletonService depends on a service "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(services=[SingletonService, ScopedService])


def test_lifetimes_match_factories() -> None:
    class ScopedService: ...

    @wireup.service(lifetime="scoped")
    def _scoped_factory() -> ScopedService:
        return ScopedService()

    @dataclass
    class SingletonService:
        scoped: ScopedService

    @wireup.service
    def _singleton_factory(scoped: ScopedService) -> SingletonService:
        return SingletonService(scoped)

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'scoped' of Type test.unit.test_container_creation.SingletonService depends on a service "
            "with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons."
        ),
    ):
        wireup.create_sync_container(services=[_scoped_factory, _singleton_factory])
