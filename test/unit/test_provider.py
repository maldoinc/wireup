from dataclasses import dataclass

import pytest
import wireup
from wireup._annotations import Injected, injectable
from wireup._decorators import inject_from_container
from wireup.errors import WireupError
from wireup.ioc.types import AsyncProvider, Provider

from test.conftest import Container
from test.unit.services import Greeter
from test.unit.services.async_reg import AsyncDependency, make_async_dependency
from test.unit.services.with_annotations.services import TransientService
from test.unit.test_container_scope import ScopedService
from test.unit.util import run


async def test_provider_returns_instance_singleton(container: Container) -> None:
    provider = await run(container.get(Provider[Greeter]))
    greeter = provider()

    assert isinstance(greeter, Greeter)
    # Assert provider-returned instance is the same as the one you'd get from the container
    assert greeter is await run(container.get(Greeter))

    # assert calling provider twice returns the same instance because it is a singleton
    assert provider() is provider()

    @inject_from_container(container)
    def _uses_provider(greeter_provider: Injected[Provider[Greeter]]) -> Greeter:
        return greeter_provider()

    # Assert instance injected via decorator is the same as the provider
    assert provider() is _uses_provider()


def test_provider_returns_instance_scoped() -> None:
    root_container = wireup.create_sync_container(
        injectables=[ScopedService],
        config={"env_name": "test"},
    )
    with root_container.enter_scope() as scope:
        provider = scope.get(Provider[ScopedService])
        scoped_service = provider()

        assert isinstance(scoped_service, ScopedService)
        # Assert provider-returned instance is the same as the one you'd get from the container
        assert scoped_service is scope.get(ScopedService)

        # assert calling provider twice returns the same instance because it is scoped
        assert provider() is provider()


def test_provider_respects_scope_boundaries() -> None:
    root = wireup.create_sync_container(injectables=[ScopedService])

    with root.enter_scope() as scope1:
        p1 = scope1.get(Provider[ScopedService])
        s1 = p1()

    with root.enter_scope() as scope2:
        p2 = scope2.get(Provider[ScopedService])
        s2 = p2()

    assert s1 is not s2


def test_provider_returns_instance_transient_no_reuse() -> None:
    root_container = wireup.create_sync_container(
        injectables=[TransientService],
    )
    with root_container.enter_scope() as scope:
        provider = scope.get(Provider[TransientService])
        scoped_service = provider()

        assert isinstance(scoped_service, TransientService)
        assert scoped_service is not scope.get(TransientService)
        assert provider() is not provider()


async def test_provider_returns_instance_async() -> None:
    container = wireup.create_async_container(injectables=[make_async_dependency])

    provider = await run(container.get(AsyncProvider[AsyncDependency]))
    async_dependency = await provider()

    assert isinstance(async_dependency, AsyncDependency)
    assert async_dependency is await run(container.get(AsyncDependency))


async def test_provider_returns_instance_async_raises_when_requesting_wrong_provider() -> None:
    container = wireup.create_async_container(injectables=[make_async_dependency])

    with pytest.raises(WireupError, match="unknown injectable"):
        # This raises since AsyncDependency has an AsyncProvider, not the synchronous one.
        await run(container.get(Provider[AsyncDependency]))


async def test_provider_respects_lifetime_rules() -> None:
    @injectable(lifetime="scoped")
    class ScopedDep:
        def __init__(self) -> None: ...

    @injectable()
    class SingletonDep:
        def __init__(self, scoped_provider: Provider[ScopedDep]) -> None: ...

    with pytest.raises(
        WireupError,
        match=rf"Parameter 'scoped_provider' of {SingletonDep!r} depends on an injectable with a 'scoped' lifetime which is not supported. Singletons can only depend on other singletons.",  # noqa: E501
    ):
        wireup.create_async_container(injectables=[SingletonDep, ScopedDep])


def test_provider_breaks_cycles() -> None:
    @dataclass
    class A:
        b: "Provider[B]"

    @dataclass
    class B:
        a: A

    @injectable
    def make_a(b: Provider[B]) -> A:
        return A(b)

    @injectable
    def make_b(a: A) -> B:
        return B(a)

    container = wireup.create_sync_container(injectables=[make_a, make_b])
    assert isinstance(container.get(A), A)
    assert isinstance(container.get(B), B)
