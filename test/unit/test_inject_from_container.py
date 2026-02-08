import contextlib
import re
from typing import Any, AsyncIterator, Iterator, NewType, Optional, Tuple, Union

import pytest
import wireup
from typing_extensions import Annotated
from wireup import Inject, Injected, create_sync_container, inject_from_container, injectable, service
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.container.async_container import ScopedAsyncContainer
from wireup.ioc.container.sync_container import ScopedSyncContainer

from test.conftest import Container
from test.unit import services
from test.unit.services.async_reg import AsyncDependency, make_async_dependency
from test.unit.services.no_annotations.random.random_service import RandomService
from test.unit.services.with_annotations.services import Foo, FooImpl, OtherFooImpl, random_service_factory


async def test_injects_targets(container: Container) -> None:
    class NotManagedByWireup: ...

    @inject_from_container(container)
    def target(
        foo: Injected[Foo],
        other_foo: Annotated[Foo, Inject(qualifier="other")],
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(config="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert isinstance(foo, Foo)
        assert isinstance(foo, FooImpl)

        assert isinstance(other_foo, Foo)
        assert isinstance(other_foo, OtherFooImpl)

        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    target(not_managed_by_wireup=NotManagedByWireup())


async def test_injects_targets_async() -> None:
    container = wireup.create_async_container(injectables=[services], config={"env_name": "test"})

    class NotManagedByWireup: ...

    @inject_from_container(container)
    def target(
        foo: Injected[Foo],
        other_foo: Annotated[Foo, Inject(qualifier="other")],
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(config="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert isinstance(foo, Foo)
        assert isinstance(foo, FooImpl)

        assert isinstance(other_foo, Foo)
        assert isinstance(other_foo, OtherFooImpl)

        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    @inject_from_container(container)
    async def async_target(
        foo: Injected[Foo],
        other_foo: Annotated[Foo, Inject(qualifier="other")],
        random_service: Annotated[RandomService, Inject(qualifier="foo")],
        env_name: Annotated[str, Inject(config="env_name")],
        env_env: Annotated[str, Inject(expr="${env_name}-${env_name}")],
        not_managed_by_wireup: NotManagedByWireup,
    ) -> None:
        assert isinstance(foo, Foo)
        assert isinstance(foo, FooImpl)

        assert isinstance(other_foo, Foo)
        assert isinstance(other_foo, OtherFooImpl)

        assert random_service.get_random() == 4
        assert env_name == "test"
        assert env_env == "test-test"
        assert isinstance(not_managed_by_wireup, NotManagedByWireup)

    target(not_managed_by_wireup=NotManagedByWireup())
    await async_target(not_managed_by_wireup=NotManagedByWireup())


def test_inject_from_container_unchecked_config() -> None:
    container = wireup.create_sync_container(config={"env_name": "test"})

    with container.enter_scope() as scoped:

        @inject_from_container_unchecked(lambda: scoped)
        def target(env_name: Annotated[str, Inject(config="env_name")]) -> str:
            return env_name

        assert target() == "test"


@pytest.mark.parametrize("qualifier", [None, "foo"])
async def test_raises_on_unknown_service(container: Container, qualifier: str) -> None:
    class NotManagedByWireup: ...

    expected_qualifier_str = f" with qualifier '{qualifier}'" if qualifier else ""
    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'not_managed_by_wireup' of Function test.unit.test_inject_from_container._ "
            "has an unknown dependency on Type test.unit.test_inject_from_container.NotManagedByWireup"
            f"{expected_qualifier_str}."
        ),
    ):

        @inject_from_container(container)
        def _(
            not_managed_by_wireup: Annotated[NotManagedByWireup, Inject(qualifier=qualifier)],
        ) -> None: ...


async def test_raises_on_unknown_parameter(container: Container) -> None:
    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'not_managed_by_wireup' of Function test.unit.test_inject_from_container._ "
            "depends on an unknown Wireup config key 'invalid'."
        ),
    ):

        @inject_from_container(container)
        def _(
            not_managed_by_wireup: Annotated[str, Inject(config="invalid")],
        ) -> None: ...


async def test_unknown_service_without_default_value() -> None:
    class UnknownClass: ...

    @service
    class BarWithoutDefaultValue:
        def __init__(self, unknown_class: UnknownClass) -> None:
            self.unknown_class = unknown_class

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Parameter 'unknown_class' of Type test.unit.test_inject_from_container.BarWithoutDefaultValue "
            "has an unknown dependency on Type test.unit.test_inject_from_container.UnknownClass."
        ),
    ):
        container = wireup.create_async_container(services=[BarWithoutDefaultValue])

        @inject_from_container(container)
        def _(
            _: Annotated[BarWithoutDefaultValue, Inject()],
        ) -> None: ...


async def test_unknown_service_with_default_value() -> None:
    class UnknownClass: ...

    @service
    class BarWithDefaultValue:
        def __init__(self, unknown_class: Optional[UnknownClass] = None) -> None:
            self.unknown_class = unknown_class

    container = wireup.create_async_container(services=[BarWithDefaultValue])

    @inject_from_container(container)
    def _(
        _: Annotated[BarWithDefaultValue, Inject()],
    ) -> None: ...


async def test_injects_service_with_provided_async_scoped_container() -> None:
    container = wireup.create_async_container(injectables=[services], config={"env_name": "test"})

    async with container.enter_scope() as scoped:

        @inject_from_container(container, lambda: scoped)
        def target(rand_service: Annotated[RandomService, Inject(qualifier="foo")]) -> None:
            assert isinstance(rand_service, RandomService)

    target()


async def test_container_sync_raises_async_def() -> None:
    container = wireup.create_sync_container(injectables=[services], config={"env_name": "test"})

    with pytest.raises(
        WireupError,
        match=re.escape(
            "Sync container cannot perform injection on async targets. "
            "Create an async container via wireup.create_async_container."
        ),
    ):

        @inject_from_container(container)
        async def _(rand_service: Annotated[RandomService, Inject(qualifier="foo")]) -> None:
            assert isinstance(rand_service, RandomService)


def test_autowire_supports_multiple_containers_does_not_patch_function():
    c1 = wireup.create_sync_container(injectables=[services], config={"env_name": "test"})
    c2 = wireup.create_sync_container(injectables=[services], config={"env_name": "test"})

    def inner(foo: Annotated[Foo, Inject()], p1: Annotated[str, Inject(config="env_name")]):
        assert isinstance(foo, Foo)
        assert p1 == "test"

    inject_from_container(c1)(inner)()
    inject_from_container(c2)(inner)()


def test_container_overrides_passed_parameters():
    c1 = wireup.create_sync_container(injectables=[services], config={"env_name": "test"})

    def inner(foo: Annotated[Foo, Inject()], p1: Annotated[str, Inject(config="env_name")]):
        assert isinstance(foo, Foo)
        assert p1 == "test"

    inject_from_container(c1)(inner)(p1="bar")


def test_container_wires_none_values_from_parameter_bag():
    container = wireup.create_async_container(config={"foo": None})

    @inject_from_container(container)
    def inner(name: Annotated[str, Inject(config="foo")], name2: Annotated[str, Inject(config="foo")]):
        assert name is None
        assert name2 is None

    inner()


def test_injects_ctor():
    container = wireup.create_async_container(injectables=[random_service_factory], config={"env": "test"})

    class Dummy:
        @inject_from_container(container)
        def __init__(
            self,
            rand_service: Annotated[RandomService, Inject(qualifier="foo")],
            env: Annotated[str, Inject(config="env")],
        ):
            self.env = env
            self.rand_service = rand_service

        def do_thing(self):
            return f"Running in {self.env} with a result of {self.rand_service.get_random()}"

    dummy = Dummy()
    assert dummy.do_thing() == "Running in test with a result of 4"


def test_inject_from_container_handles_optionals() -> None:
    class MaybeThing: ...

    def make_maybe_thing() -> Optional[MaybeThing]:
        return None

    class Thing: ...

    def make_thing(_thing2: Optional[MaybeThing]) -> Thing:
        return Thing()

    container = wireup.create_sync_container(
        injectables=[wireup.injectable(make_maybe_thing), wireup.injectable(make_thing)]
    )

    @wireup.inject_from_container(container)
    def main(maybe_thing: Injected[Optional[MaybeThing]], thing: Injected[Thing]):
        assert maybe_thing is None
        assert isinstance(thing, Thing)

    main()


async def test_raises_generator_cleanup() -> None:
    Something = NewType("Something", str)
    exception_notified = False

    @wireup.injectable(lifetime="scoped")
    async def f1() -> AsyncIterator[Something]:
        try:
            yield Something("Something")
        except:  # noqa: E722
            nonlocal exception_notified
            exception_notified = True

    c = wireup.create_async_container(injectables=[f1])

    @inject_from_container(c)
    async def main(_: Injected[Something]):
        raise ValueError("boom!")

    with contextlib.suppress(Exception):
        await main()

    assert exception_notified


async def test_inject_from_container_middleware() -> None:
    Something = NewType("Something", str)
    middleware_called = False

    @wireup.injectable(lifetime="scoped")
    def f1() -> Something:
        return Something("Something")

    def middleware(
        scoped_container: Union[ScopedAsyncContainer, ScopedSyncContainer],  # noqa: ARG001
        *args: Any,  # noqa: ARG001
        **kwargs: Any,  # noqa: ARG001
    ) -> Iterator[None]:
        nonlocal middleware_called
        middleware_called = True
        try:
            yield
        finally:
            pass

    c = wireup.create_async_container(injectables=[f1])

    @inject_from_container(c, _middleware=middleware)
    async def main(_: Injected[Something]): ...

    await main()

    assert middleware_called


async def test_inject_from_container_middleware_cleanup_on_error() -> None:
    Something = NewType("Something", str)
    cleanup_ran = False

    @wireup.injectable(lifetime="scoped")
    def f1() -> Something:
        return Something("Something")

    def middleware(
        scoped_container: Union[ScopedAsyncContainer, ScopedSyncContainer],  # noqa: ARG001
        *args: Any,  # noqa: ARG001
        **kwargs: Any,  # noqa: ARG001
    ) -> Iterator[None]:
        nonlocal cleanup_ran
        try:
            yield
        finally:
            cleanup_ran = True

    c = wireup.create_async_container(injectables=[f1])

    @inject_from_container(c, _middleware=middleware)
    async def main(_: Injected[Something]):
        raise ValueError("boom!")

    with pytest.raises(ValueError, match="boom!"):
        await main()

    assert cleanup_ran


def test_inject_from_container_generator(container: Container) -> None:
    @inject_from_container(container)
    def generator_target(
        foo: Injected[Foo],
        env_name: Annotated[str, Inject(config="env_name")],
    ) -> Iterator[str]:
        assert isinstance(foo, Foo)
        assert env_name == "test"
        yield env_name
        yield "after_yield"

    gen = generator_target()
    assert next(gen) == "test"
    assert next(gen) == "after_yield"
    with contextlib.suppress(StopIteration):
        next(gen)


def test_inject_from_container_context_manager(container: Container) -> None:
    # Test that inject_from_container works with contextlib.contextmanager targets

    @inject_from_container(container)
    @contextlib.contextmanager
    def _context_manager_target(
        foo: Injected[Foo],
        env_name: Annotated[str, Inject(config="env_name")],
    ) -> Iterator[str]:
        assert isinstance(foo, Foo)
        assert env_name == "test"
        yield env_name

    with _context_manager_target() as val:
        assert val == "test"


async def test_inject_from_container_async_generator() -> None:
    container = wireup.create_async_container(injectables=[services], config={"env_name": "test"})

    @inject_from_container(container)
    async def async_generator_target(
        foo: Injected[Foo],
        env_name: Annotated[str, Inject(config="env_name")],
    ) -> AsyncIterator[str]:
        assert isinstance(foo, Foo)
        assert env_name == "test"
        yield env_name
        yield "after_yield"

    gen = async_generator_target()
    assert await gen.__anext__() == "test"
    assert await gen.__anext__() == "after_yield"
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_async_injects_sync_reuses_async_dependency_in_sync_context() -> None:
    container = wireup.create_async_container(injectables=[make_async_dependency])

    # Injection fails here since the current sync scope cannot create the async dependency.
    @inject_from_container(container)
    def sync_func_fail(a: Injected[AsyncDependency]) -> None:
        pass

    with pytest.raises(WireupError, match="is an async dependency and it cannot be created in a synchronous context"):
        sync_func_fail()

    inst = await container.get(AsyncDependency)

    # Dependency is already created so just reuse the instance.
    @inject_from_container(container)
    def sync_func_success(a: Injected[AsyncDependency]) -> AsyncDependency:
        return a

    assert sync_func_success() is inst


def test_async_override_with_sync_value_in_sync_context(container: Container) -> None:
    fake_b = AsyncDependency()
    with container.override.injectable(AsyncDependency, fake_b):

        @inject_from_container(container)
        def sync_func_override(b: Injected[AsyncDependency]) -> AsyncDependency:
            return b

        assert sync_func_override() is fake_b


@injectable
class SingletonService:
    pass


@injectable(lifetime="scoped")
class ScopedService:
    pass


@injectable(lifetime="scoped")
class ScopedService2:
    pass


def test_mixed_lifetime_injection_optimizes_correctly_singleton_first() -> None:
    container = create_sync_container(injectables=[SingletonService, ScopedService, ScopedService2])

    @inject_from_container(container)
    def target(
        s: Injected[SingletonService], sc: Injected[ScopedService], ss2: Injected[ScopedService2]
    ) -> Tuple[SingletonService, ScopedService, ScopedService2]:
        return s, sc, ss2

    s, sc, ss2 = target()
    assert s is container.get(SingletonService)
    assert isinstance(sc, ScopedService)
    assert isinstance(ss2, ScopedService2)


def test_mixed_lifetime_injection_optimizes_correctly_scoped_first() -> None:
    container = create_sync_container(injectables=[SingletonService, ScopedService])

    @inject_from_container(container)
    def target(sc: Injected[ScopedService], s: Injected[SingletonService]) -> Tuple[SingletonService, ScopedService]:
        return s, sc

    s, sc = target()
    assert s is container.get(SingletonService)
    assert isinstance(sc, ScopedService)
