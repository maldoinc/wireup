import asyncio

from wireup import create_async_container, injectable


class Counter:
    pass


async def counter_factory() -> Counter:
    await asyncio.sleep(0.01)
    return Counter()


async def test_singleton_concurrency() -> None:
    container = create_async_container(services=[injectable(counter_factory)])

    results = await asyncio.gather(
        container.get(Counter),
        container.get(Counter),
        container.get(Counter),
        container.get(Counter),
        container.get(Counter),
    )

    unique_instances = set(results)
    assert len(unique_instances) == 1, f"Expected 1 singleton instance, got {len(unique_instances)}"


async def test_scoped_concurrency_same_scope() -> None:
    container = create_async_container(
        services=[injectable(counter_factory, lifetime="scoped")], concurrent_scoped_access=True
    )

    async with container.enter_scope() as scope:
        results = await asyncio.gather(
            scope.get(Counter),
            scope.get(Counter),
            scope.get(Counter),
            scope.get(Counter),
            scope.get(Counter),
        )

        unique_instances = set(results)
        assert len(unique_instances) == 1, f"Expected 1 scoped instance within same scope, got {len(unique_instances)}"


async def test_scoped_concurrency_same_scope_no_lock_race() -> None:
    container = create_async_container(services=[injectable(counter_factory, lifetime="scoped")])

    async with container.enter_scope() as scope:
        results = await asyncio.gather(
            scope.get(Counter),
            scope.get(Counter),
            scope.get(Counter),
            scope.get(Counter),
            scope.get(Counter),
        )

        unique_instances = set(results)
        # With sleep in factory and no lock, there should be multiple instances due to race conditions.
        assert len(unique_instances) > 1


async def test_scoped_concurrency_different_scopes() -> None:
    container = create_async_container(services=[injectable(counter_factory, lifetime="scoped")])

    async with container.enter_scope() as scope1:
        async with container.enter_scope() as scope2:
            res1, res2 = await asyncio.gather(scope1.get(Counter), scope2.get(Counter))

            assert res1 is not res2, "Different scopes should produce different instances"


async def test_singleton_concurrency_cross_scope() -> None:
    container = create_async_container(services=[injectable(counter_factory)])

    async with container.enter_scope() as scope1, container.enter_scope() as scope2:
        # Concurrently request the SINGLETON from two different scopes
        results = await asyncio.gather(
            scope1.get(Counter),
            scope1.get(Counter),
            scope1.get(Counter),
            scope2.get(Counter),
            scope2.get(Counter),
            scope2.get(Counter),
            scope2.get(Counter),
            container.get(Counter),
        )

        unique_instances = set(results)
        assert len(unique_instances) == 1, f"Expected 1 singleton instance, got {len(unique_instances)}"
