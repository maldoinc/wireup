from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Iterator

import pytest
import wireup
from wireup import (
    AsyncContainer,
    Injected,
    SyncContainer,
    create_async_container,
    create_sync_container,
    inject_from_container,
    injectable,
)
from wireup._decorators import inject_from_container_unchecked
from wireup.errors import WireupError
from wireup.ioc.factory_compiler import FactoryCompiler

if TYPE_CHECKING:
    from wireup.ioc.container.async_container import ScopedAsyncContainer
    from wireup.ioc.container.sync_container import ScopedSyncContainer


@injectable
@dataclass
class SingletonService:
    pass


@injectable(lifetime="scoped")
@dataclass
class ScopedService:
    pass


@dataclass
class AsyncService:
    pass


@injectable
async def async_service_factory() -> AsyncService:
    return AsyncService()


@pytest.fixture
def sync_container() -> SyncContainer:
    return create_sync_container(injectables=[SingletonService, ScopedService], config={"foo": "bar"})


@pytest.fixture
def async_container() -> AsyncContainer:
    return create_async_container(
        injectables=[SingletonService, ScopedService, async_service_factory], config={"foo": "bar"}
    )


def _get_generated_code(fn: Any) -> str:
    if not hasattr(fn, "__wireup_generated_code__"):
        pytest.fail("Target has no generated code.")
    return fn.__wireup_generated_code__


def singleton_config_target(
    s: Injected[SingletonService],
    conf: Annotated[str, wireup.Inject(config="foo")],
) -> None:
    pass


def singleton_scoped_config_target(
    s: Injected[SingletonService],
    sc: Injected[ScopedService],
    conf: Annotated[str, wireup.Inject(config="foo")],
) -> None:
    pass


async def async_singleton_config_target(
    s: Injected[SingletonService],
    conf: Annotated[str, wireup.Inject(config="foo")],
) -> None:
    pass


async def async_singleton_scoped_config_target(
    s: Injected[SingletonService],
    sc: Injected[ScopedService],
    conf: Annotated[str, wireup.Inject(config="foo")],
) -> None:
    pass


def sync_target_with_async_dep(
    asvc: Injected[AsyncService],
) -> None:
    pass


async def async_target_with_async_dep(
    asvc: Injected[AsyncService],
) -> None:
    pass


def middleware(_container: ScopedSyncContainer | ScopedAsyncContainer, _args: Any, _kwargs: Any) -> Iterator[None]:
    yield None


s_hash = FactoryCompiler.get_object_id(SingletonService, None)
sc_hash = FactoryCompiler.get_object_id(ScopedService, None)


def test_sync_container_singleton_scoped_config_optimized(sync_container: SyncContainer):
    """
    Test SyncContainer injecting into a Sync Target with Singleton, Scoped, and Config dependencies.

    **Scenario**:
    -   Container: `SyncContainer`
    -   Target: Sync Function
    -   Dependencies: Singleton, Scoped, Config

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   A scope is explicitly entered.
    -   Optimized factory lookups are used for both Singleton and Scoped dependencies.
    """
    decorated = inject_from_container(sync_container)(singleton_scoped_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        def _wireup_generated_wrapper(*args, **kwargs):
            with _wireup_container.enter_scope() as scope:
                kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
                kwargs['sc'] = _wireup_scoped_factories[{sc_hash}].factory(scope)
                kwargs['conf'] = _wireup_config_val_conf
                return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_sync_container_singleton_config_optimized(sync_container: SyncContainer):
    """
    Test SyncContainer injecting into a Sync Target with Singleton and Config dependencies.

    **Scenario**:
    -   Container: `SyncContainer`
    -   Target: Sync Function
    -   Dependencies: Singleton, Config (No Scoped dependencies)

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   No scope is entered (Optimization).
    -   Optimized factory lookup is used for the Singleton.
    """
    decorated = inject_from_container(sync_container)(singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
            kwargs['conf'] = _wireup_config_val_conf
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_sync_container_singleton_config_with_middleware(sync_container: SyncContainer):
    """
    Test SyncContainer injecting into a Sync Target with Middleware.

    **Scenario**:
    -   Container: `SyncContainer`
    -   Target: Sync Function
    -   Dependencies: Singleton, Config
    -   Middleware: Present

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   A scope is explicitly entered to support middleware execution.
    -   Middleware is invoked and cleaned up.
    -   Optimized factory lookup is used.
    """
    decorated = inject_from_container(sync_container, _middleware=middleware)(singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        def _wireup_generated_wrapper(*args, **kwargs):
            with _wireup_container.enter_scope() as scope:
                gen_middleware = _wireup_middleware(scope, args, kwargs)
                try:
                    next(gen_middleware)
                    kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
                    kwargs['conf'] = _wireup_config_val_conf
                    return _wireup_target(*args, **kwargs)
                finally:
                    gen_middleware.close()
    """).strip()

    assert code.strip() == expected


def test_async_container_sync_target_optimization_behavior(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into a Sync Target with mixed dependencies.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Sync Function
    -   Dependencies: Singleton (Sync), AsyncService (Async Dep)

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   **Singleton**: Uses optimized factory lookup.
    -   **Async Service**: Uses unoptimized fallback (`scope._synchronous_get`), as Async dependencies cannot be
        retrieved synchronously unless already cached/overridden.
    """

    def target(
        s: Injected[SingletonService],
        asvc: Injected[AsyncService],
    ) -> None:
        pass

    decorated = inject_from_container(async_container)(target)
    code = _get_generated_code(decorated)

    s_hash = FactoryCompiler.get_object_id(SingletonService, None)

    expected = textwrap.dedent(f"""
        def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
            kwargs['asvc'] = scope._synchronous_get(_wireup_obj_asvc_klass)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_async_container_async_target_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into an Async Target with mixed dependencies.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Async Function
    -   Dependencies: Singleton (Sync), AsyncService (Async Dep)

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   Both dependencies use optimized factory lookups.
    -   Async factory (`AsyncService`) is awaited.
    """

    async def target(
        s: Injected[SingletonService],
        asvc: Injected[AsyncService],
    ) -> None:
        pass

    decorated = inject_from_container(async_container)(target)
    code = _get_generated_code(decorated)

    s_hash = FactoryCompiler.get_object_id(SingletonService, None)
    asvc_hash = FactoryCompiler.get_object_id(AsyncService, None)

    expected = textwrap.dedent(f"""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
            kwargs['asvc'] = await _wireup_singleton_factories[{asvc_hash}].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_sync_container_rejects_async_target(sync_container: AsyncContainer):
    """
    Test that SyncContainer explicitly rejects Async Targets.

    **Scenario**:
    -   Container: `SyncContainer`
    -   Target: Async Function
    """

    async def target(s: Injected[SingletonService]) -> None:
        pass

    with pytest.raises(WireupError, match="Sync container cannot perform injection on async targets"):
        inject_from_container(sync_container)(target)


def test_async_container_sync_target_singleton_config_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into a Sync Target with Singleton and Config.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Sync Function
    -   Dependencies: Singleton, Config

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   No scope is entered (Optimization).
    -   Uses `_wireup_container` (AsyncContainer) as the scope for the Singleton factory.
    """
    decorated = inject_from_container(async_container)(singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
            kwargs['conf'] = _wireup_config_val_conf
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_async_container_sync_target_singleton_scoped_config_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into a Sync Target with Scoped dependency.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Sync Function
    -   Dependencies: Singleton, Scoped, Config

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   Forces a synchronous scope (`_wireup_async_container_force_sync_scope`)
        to allow synchronous resolution of scoped components.
    """
    decorated = inject_from_container(async_container)(singleton_scoped_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        def _wireup_generated_wrapper(*args, **kwargs):
            with _wireup_async_container_force_sync_scope(_wireup_container) as scope:
                kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
                kwargs['sc'] = _wireup_scoped_factories[{sc_hash}].factory(scope)
                kwargs['conf'] = _wireup_config_val_conf
                return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_async_container_async_target_singleton_config_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into an Async Target with Singleton and Config.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Async Function
    -   Dependencies: Singleton, Config

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   No scope is entered (Optimization).
    -   Optimized factory lookup used.
    -   No needless call to await container.get
    """
    decorated = inject_from_container(async_container)(async_singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
            kwargs['conf'] = _wireup_config_val_conf
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_async_container_async_target_singleton_scoped_config_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into an Async Target with Scoped dependency.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Async Function
    -   Dependencies: Singleton, Scoped, Config

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   Enters an async scope.
    -   Optimized factory lookups used.
    """
    decorated = inject_from_container(async_container)(async_singleton_scoped_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent(f"""
        async def _wireup_generated_wrapper(*args, **kwargs):
            async with _wireup_container.enter_scope() as scope:
                kwargs['s'] = _wireup_singleton_factories[{s_hash}].factory(scope)
                kwargs['sc'] = _wireup_scoped_factories[{sc_hash}].factory(scope)
                kwargs['conf'] = _wireup_config_val_conf
                return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_sync_container_rejects_async_targets_all(sync_container: SyncContainer):
    """
    Test that SyncContainer rejects all forms of Async Targets.
    """
    for target in [async_singleton_config_target, async_singleton_scoped_config_target]:
        with pytest.raises(WireupError, match="Sync container cannot perform injection on async targets"):
            inject_from_container(sync_container)(target)


def test_unchecked_sync_container_singleton_config_optimized(sync_container: SyncContainer):
    """
    Test Unchecked Injection: SyncContainer -> Sync Target (Singleton+Config).

    **Scenario**:
    -   Container: `SyncContainer` (Unchecked)
    -   Target: Sync Function

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Bypasses optimizations.
    -   Manually retrieves scope from supplier and uses `_synchronous_get`.
    -   Fetches config from scope at runtime.
    """
    decorated = inject_from_container_unchecked(lambda: sync_container.enter_scope())(singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = scope._synchronous_get(_wireup_obj_s_klass)
            kwargs['conf'] = scope.config.get(_wireup_config_key_conf)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_sync_container_singleton_scoped_config_optimized(sync_container: SyncContainer):
    """
    Test Unchecked Injection: SyncContainer -> Sync Target (Singleton+Scoped+Config).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Bypasses optimizations.
    -   Manually retrieves scope.
    -   Uses `_synchronous_get` for all dependencies.
    """
    decorated = inject_from_container_unchecked(lambda: sync_container.enter_scope())(singleton_scoped_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = scope._synchronous_get(_wireup_obj_s_klass)
            kwargs['sc'] = scope._synchronous_get(_wireup_obj_sc_klass)
            kwargs['conf'] = scope.config.get(_wireup_config_key_conf)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_async_container_sync_target_singleton_config_optimized(async_container: AsyncContainer):
    """
    Test Unchecked Injection: AsyncContainer -> Sync Target (Singleton+Config).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Uses `_synchronous_get` (Fallback for async container in sync context).
    """
    decorated = inject_from_container_unchecked(lambda: async_container.enter_scope())(singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = scope._synchronous_get(_wireup_obj_s_klass)
            kwargs['conf'] = scope.config.get(_wireup_config_key_conf)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_async_container_sync_target_singleton_scoped_config_optimized(async_container: AsyncContainer):
    """
    Test Unchecked Injection: AsyncContainer -> Sync Target (Singleton+Scoped+Config).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Uses `_synchronous_get` for all dependencies.
    """
    decorated = inject_from_container_unchecked(lambda: async_container.enter_scope())(singleton_scoped_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = scope._synchronous_get(_wireup_obj_s_klass)
            kwargs['sc'] = scope._synchronous_get(_wireup_obj_sc_klass)
            kwargs['conf'] = scope.config.get(_wireup_config_key_conf)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_async_container_async_target_singleton_config_optimized(async_container: AsyncContainer):
    """
    Test Unchecked Injection: AsyncContainer -> Async Target (Singleton+Config).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Uses `await scope.get(...)` for dependencies.
    """
    decorated = inject_from_container_unchecked(lambda: async_container.enter_scope())(async_singleton_config_target)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = await scope.get(_wireup_obj_s_klass)
            kwargs['conf'] = scope.config.get(_wireup_config_key_conf)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_async_container_async_target_singleton_scoped_config_optimized(async_container: AsyncContainer):
    """
    Test Unchecked Injection: AsyncContainer -> Async Target (Singleton+Scoped+Config).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Uses `await scope.get(...)` for all dependencies.
    """
    decorated = inject_from_container_unchecked(lambda: async_container.enter_scope())(
        async_singleton_scoped_config_target
    )
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['s'] = await scope.get(_wireup_obj_s_klass)
            kwargs['sc'] = await scope.get(_wireup_obj_sc_klass)
            kwargs['conf'] = scope.config.get(_wireup_config_key_conf)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_async_container_sync_target_async_dep_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into a Sync Target with an Async Dependency.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Sync Function
    -   Dependency: Async (`AsyncService`)

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   Fallback to `scope._synchronous_get`. This will see if an instance already exists before giving up.
    """
    decorated = inject_from_container(async_container)(sync_target_with_async_dep)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['asvc'] = scope._synchronous_get(_wireup_obj_asvc_klass)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_async_container_async_target_async_dep_optimized(async_container: AsyncContainer):
    """
    Test AsyncContainer injecting into an Async Target with an Async Dependency.

    **Scenario**:
    -   Container: `AsyncContainer`
    -   Target: Async Function
    -   Dependency: Async (`AsyncService`)

    **Optimization**:
    -   Optimized: We know the container, it's always this one.

    **Expectation**:
    -   Optimized factory lookup is used.
    -   Factory result is awaited (`await ...factory(scope)`).
    """
    decorated = inject_from_container(async_container)(async_target_with_async_dep)
    code = _get_generated_code(decorated)

    asvc_hash = FactoryCompiler.get_object_id(AsyncService, None)
    expected = textwrap.dedent(f"""
        async def _wireup_generated_wrapper(*args, **kwargs):
            kwargs['asvc'] = await _wireup_singleton_factories[{asvc_hash}].factory(scope)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_async_container_sync_target_async_dep_optimized(async_container: AsyncContainer):
    """
    Test Unchecked Injection: AsyncContainer -> Sync Target (Async Dependency).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Bypasses optimization.
    -   Uses `scope._synchronous_get`.
    """
    decorated = inject_from_container_unchecked(lambda: async_container.enter_scope())(sync_target_with_async_dep)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['asvc'] = scope._synchronous_get(_wireup_obj_asvc_klass)
            return _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected


def test_unchecked_async_container_async_target_async_dep_optimized(async_container: AsyncContainer):
    """
    Test Unchecked Injection: AsyncContainer -> Async Target (Async Dependency).

    **Optimization**:
    -   Unoptimized: Container is not known until execution time when we get it from the supplier.

    **Expectation**:
    -   Bypasses optimization.
    -   Uses `await scope.get(...)`.
    """
    decorated = inject_from_container_unchecked(lambda: async_container.enter_scope())(async_target_with_async_dep)
    code = _get_generated_code(decorated)

    expected = textwrap.dedent("""
        async def _wireup_generated_wrapper(*args, **kwargs):
            scope = _wireup_scoped_container_supplier()
            kwargs['asvc'] = await scope.get(_wireup_obj_asvc_klass)
            return await _wireup_target(*args, **kwargs)
    """).strip()

    assert code.strip() == expected
