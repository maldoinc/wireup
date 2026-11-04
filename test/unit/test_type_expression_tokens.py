from collections.abc import Callable

from typing_extensions import TypeAliasType
from wireup import create_async_container, injectable, qualified


class Service:
    pass


Selector = TypeAliasType("Selector", Callable[[str], Service])


@injectable(qualifier="optional")
def optional_service() -> Service | None:
    return None


@injectable(qualifier="selector", lifetime="scoped")
def service_selector() -> Selector:
    return lambda _: Service()


async def test_type_expression_tokens_support_resolution_overrides_and_provided_scope() -> None:
    container = create_async_container(injectables=[optional_service, service_selector])
    async with container.enter_scope() as scope:
        assert await scope.get(Service | None, qualifier="optional") is None
        select = await scope.get(Selector, qualifier="selector")
        assert isinstance(select("first"), Service)

    replacement = Service()
    with container.override({qualified(Service | None, "optional"): replacement}):
        assert await container.get(Service | None, qualifier="optional") is replacement

    def select_replacement(_: str) -> Service:
        return replacement

    async with container.enter_scope({qualified(Selector, "selector"): select_replacement}) as scope:
        select = await scope.get(Selector, qualifier="selector")
        assert select("provided") is replacement
    await container.close()
