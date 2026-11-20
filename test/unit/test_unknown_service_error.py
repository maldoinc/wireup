from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import pytest
import wireup
from wireup import injectable
from wireup.errors import UnknownServiceRequestedError


class _UnregisteredFoo:
    pass


class _RegisteredFoo:
    pass


@injectable
class _FooWithFactory:
    pass


class _Proto(Protocol):
    def value(self) -> str: ...


def test_unknown_type_without_qualifier_sync() -> None:
    container = wireup.create_sync_container()
    full_name = f"{_UnregisteredFoo.__module__}.{_UnregisteredFoo.__qualname__}"

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(_UnregisteredFoo)

    assert str(exc_info.value) == (
        f"Cannot create '{full_name}'\n\n"
        f"Type '{full_name}' is not known to the container.\n\n"
        "How to fix:\n"
        "  Register it with the container using @injectable:\n\n"
        "    @injectable\n"
        "    class _UnregisteredFoo: ...\n\n"
        "  Then include it in your container:\n"
        "    container = wireup.create_sync_container(\n"
        "        injectables=[_UnregisteredFoo],  # Direct registration\n"
        "        # or\n"
        "        injectables=[app.services],      # Package registration\n"
        "    )\n\n"
        "Documentation: https://maldoinc.github.io/wireup/latest/injectables/"
    )


async def test_unknown_type_with_qualifier_async() -> None:
    container = wireup.create_async_container()
    full_name = f"{_UnregisteredFoo.__module__}.{_UnregisteredFoo.__qualname__}"

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        await container.get(_UnregisteredFoo, qualifier="bar")

    assert str(exc_info.value) == (
        f"Cannot create '{full_name}' with qualifier 'bar'\n\n"
        f"Type '{full_name}' is not known to the container.\n\n"
        "How to fix:\n"
        "  Register it with the container using @injectable:\n\n"
        '    @injectable(qualifier="bar")\n'
        "    class _UnregisteredFoo: ...\n\n"
        "  Then include it in your container:\n"
        "    container = wireup.create_async_container(\n"
        "        injectables=[_UnregisteredFoo],  # Direct registration\n"
        "        # or\n"
        "        injectables=[app.services],      # Package registration\n"
        "    )\n\n"
        "Documentation: https://maldoinc.github.io/wireup/latest/injectables/"
    )


def test_unknown_type_with_falsy_non_string_qualifier() -> None:
    container = wireup.create_sync_container()
    full_name = f"{_UnregisteredFoo.__module__}.{_UnregisteredFoo.__qualname__}"

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(_UnregisteredFoo, qualifier=0)

    message = str(exc_info.value)
    assert f"Cannot create '{full_name}' with qualifier 0" in message
    assert "@injectable(qualifier=0)" in message


def test_known_type_unknown_qualifier_class_and_factory() -> None:
    @injectable(qualifier="foo")
    def create_foo() -> _FooWithFactory:
        return _FooWithFactory()

    container = wireup.create_sync_container(injectables=[_FooWithFactory, create_foo])
    full_name = f"{_FooWithFactory.__module__}.{_FooWithFactory.__qualname__}"

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(_FooWithFactory, qualifier="bar")

    assert str(exc_info.value) == (
        f"Cannot create '{full_name}' with qualifier 'bar'\n\n"
        f"Type '{full_name}' is registered, but not with the qualifier 'bar'.\n\n"
        "Available qualifiers:\n"
        "  (default) -> registered via class _FooWithFactory\n"
        '  "foo"     -> registered via create_foo()\n\n'
        "How to fix:\n"
        "  Option 1: Use an existing qualifier.\n\n"
        "  Option 2: Register with the 'bar' qualifier:\n"
        '    @injectable(qualifier="bar")\n'
        "    class _FooWithFactory: ...\n\n"
        '    @injectable(qualifier="bar")\n'
        "    def create_foo_with_factory() -> _FooWithFactory: ...\n\n"
        "Documentation: https://maldoinc.github.io/wireup/latest/injectables/"
    )


def test_known_type_unknown_qualifier_class_only() -> None:
    @injectable
    class UserService:
        pass

    container = wireup.create_sync_container(injectables=[UserService])

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(UserService, qualifier="alt")

    message = str(exc_info.value)
    assert "(default) -> registered via class UserService" in message
    assert '    @injectable(qualifier="alt")\n    class UserService: ...' in message
    assert "def create_user_service" not in message


def test_known_type_unknown_qualifier_factory_only() -> None:
    @injectable(qualifier="primary")
    def build_service() -> _RegisteredFoo:
        return _RegisteredFoo()

    container = wireup.create_sync_container(injectables=[build_service])

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(_RegisteredFoo, qualifier="secondary")

    message = str(exc_info.value)
    assert '"primary" -> registered via build_service()' in message
    assert '    @injectable(qualifier="secondary")\n    def create_registered_foo() -> _RegisteredFoo: ...' in message
    assert "class _RegisteredFoo: ..." not in message


async def test_known_type_requested_without_qualifier() -> None:
    @injectable(as_type=_Proto, qualifier="foo")
    class Impl:
        def value(self) -> str:
            return "ok"

    container = wireup.create_async_container(injectables=[Impl])
    full_name = f"{_Proto.__module__}.{_Proto.__qualname__}"

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        await container.get(_Proto)

    assert str(exc_info.value) == (
        f"Cannot create '{full_name}'\n\n"
        f"Type '{full_name}' is registered, but not without a qualifier.\n\n"
        "Available qualifiers:\n"
        '  "foo" -> registered via class Impl\n\n'
        "How to fix:\n"
        "  Option 1: Use an existing qualifier.\n\n"
        "  Option 2: Register without a qualifier:\n"
        "    @injectable\n"
        "    class _Proto: ...\n\n"
        "Documentation: https://maldoinc.github.io/wireup/latest/injectables/"
    )


def test_known_type_with_non_string_falsy_qualifier_listed() -> None:
    @injectable(qualifier=0)
    def make_zero() -> _RegisteredFoo:
        return _RegisteredFoo()

    container = wireup.create_sync_container(injectables=[make_zero])

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(_RegisteredFoo, qualifier=1)

    message = str(exc_info.value)
    assert "0 -> registered via make_zero()" in message
    assert "@injectable(qualifier=1)" in message


def test_unknown_generic_type_does_not_crash() -> None:
    container = wireup.create_sync_container()

    with pytest.raises(UnknownServiceRequestedError) as exc_info:
        container.get(Sequence[_UnregisteredFoo])

    assert "is not known to the container." in str(exc_info.value)


def test_direct_error_instantiation_remains_backwards_compatible() -> None:
    err = UnknownServiceRequestedError(_UnregisteredFoo)
    assert "is not known to the container." in str(err)
    assert "with qualifier" not in str(err)
